import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.translation import async_get_translations

from .api import (
    PlantLabApiClient,
    PlantLabAuthError,
    PlantLabConnectionError,
    PlantLabRateLimitError,
)
from .const import (
    ATTR_ENTITY_ID,
    ATTR_IMAGE_PATH,
    CONF_API_KEY,
    CONF_CAMERA_ENTITY,
    CONF_DAILY_TIME,
    CONF_FIRST_RUN_NOTIFIED,
    CONF_HOST,
    DEFAULT_HOST,
    DOMAIN,
    OPTIONS_URL,
    SERVICE_DIAGNOSE,
)
from .coordinator import HistoryCoordinator
from .sensor import SIGNAL_DIAGNOSIS_UPDATE

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "button"]

ENTRY_KEY_CLIENT = "client"
ENTRY_KEY_HISTORY_COORDINATOR = "history_coordinator"
ENTRY_KEY_UNSUB_SCHEDULE = "unsub_schedule"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = PlantLabApiClient(
        session=async_get_clientsession(hass),
        api_key=entry.data[CONF_API_KEY],
        host=entry.data.get(CONF_HOST, DEFAULT_HOST),
    )
    history_coordinator = HistoryCoordinator(hass, entry, client)
    await history_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    entry_data = {
        ENTRY_KEY_CLIENT: client,
        ENTRY_KEY_HISTORY_COORDINATOR: history_coordinator,
        ENTRY_KEY_UNSUB_SCHEDULE: None,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_diagnose(call: ServiceCall) -> ServiceResponse:
        entity_id = call.data.get(ATTR_ENTITY_ID)
        image_path = call.data.get(ATTR_IMAGE_PATH)

        if not entity_id and not image_path:
            raise ServiceValidationError("Must provide either entity_id (camera) or image_path")

        if entity_id:
            image_bytes = await _get_image_from_camera(hass, entity_id)
            filename = "snapshot.jpg"
        else:
            if not hass.config.is_allowed_path(image_path):
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="path_not_allowed",
                    translation_placeholders={"path": image_path},
                )
            image_bytes = await hass.async_add_executor_job(_read_image_file, image_path)
            filename = image_path.rsplit("/", 1)[-1] if "/" in image_path else image_path

        return await async_run_diagnosis(hass, client, image_bytes, filename)

    hass.services.async_register(
        DOMAIN,
        SERVICE_DIAGNOSE,
        handle_diagnose,
        supports_response=SupportsResponse.ONLY,
    )

    _setup_daily_diagnosis(hass, entry, client, entry_data)
    await _notify_first_run(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_run_diagnosis(
    hass: HomeAssistant, client: PlantLabApiClient, image_bytes: bytes, filename: str
) -> dict:
    """Send an image to PlantLab and update the sensors. Shared by the service, the button, and the schedule."""
    try:
        result = await client.async_diagnose(image_bytes, filename=filename)
    except PlantLabAuthError as err:
        raise HomeAssistantError(f"Authentication failed: {err}") from err
    except PlantLabRateLimitError as err:
        raise HomeAssistantError(str(err)) from err
    except PlantLabConnectionError as err:
        raise HomeAssistantError(f"PlantLab API error: {err}") from err

    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, result)
    return result


async def async_diagnose_camera(hass: HomeAssistant, client: PlantLabApiClient, camera_entity_id: str) -> dict:
    image_bytes = await _get_image_from_camera(hass, camera_entity_id)
    return await async_run_diagnosis(hass, client, image_bytes, "snapshot.jpg")


def _setup_daily_diagnosis(
    hass: HomeAssistant, entry: ConfigEntry, client: PlantLabApiClient, entry_data: dict
) -> None:
    camera_entity_id = entry.options.get(CONF_CAMERA_ENTITY)
    daily_time = entry.options.get(CONF_DAILY_TIME)
    if not camera_entity_id or not daily_time:
        return

    hour, minute, second = (int(part) for part in daily_time.split(":"))

    async def run_daily_diagnosis(_now) -> None:
        try:
            await async_diagnose_camera(hass, client, camera_entity_id)
        except HomeAssistantError as err:
            _LOGGER.warning("Daily PlantLab diagnosis failed: %s", err)

    entry_data[ENTRY_KEY_UNSUB_SCHEDULE] = async_track_time_change(
        hass, run_daily_diagnosis, hour=hour, minute=minute, second=second
    )


async def _notify_first_run(hass: HomeAssistant, entry: ConfigEntry) -> None:
    notification_id = f"{DOMAIN}_first_diagnosis_{entry.entry_id}"
    if entry.options.get(CONF_CAMERA_ENTITY) and entry.options.get(CONF_DAILY_TIME):
        persistent_notification.async_dismiss(hass, notification_id)
        return
    if entry.data.get(CONF_FIRST_RUN_NOTIFIED):
        return

    texts = await async_get_translations(hass, hass.config.language, "exceptions", integrations={DOMAIN})
    prefix = f"component.{DOMAIN}.exceptions."
    persistent_notification.async_create(
        hass,
        texts[f"{prefix}first_diagnosis_body.message"].replace("{options_url}", OPTIONS_URL),
        title=texts[f"{prefix}first_diagnosis_title.message"],
        notification_id=notification_id,
    )
    hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_FIRST_RUN_NOTIFIED: True})


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data and entry_data[ENTRY_KEY_UNSUB_SCHEDULE]:
            entry_data[ENTRY_KEY_UNSUB_SCHEDULE]()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_DIAGNOSE)
            hass.data.pop(DOMAIN)
    return unload_ok


async def _get_image_from_camera(hass: HomeAssistant, entity_id: str) -> bytes:
    from homeassistant.components.camera import async_get_image

    try:
        image = await async_get_image(hass, entity_id)
        return image.content
    except HomeAssistantError:
        raise
    except Exception as err:
        raise HomeAssistantError(f"Failed to get image from camera {entity_id}: {err}") from err


def _read_image_file(path: str) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError as err:
        raise HomeAssistantError(f"Image file not found: {path}") from err
    except OSError as err:
        raise HomeAssistantError(f"Error reading image file {path}: {err}") from err
