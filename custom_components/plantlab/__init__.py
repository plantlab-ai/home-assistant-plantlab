from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

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
    CONF_HOST,
    DEFAULT_HOST,
    DOMAIN,
    SERVICE_DIAGNOSE,
)
from .sensor import SIGNAL_DIAGNOSIS_UPDATE

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = PlantLabApiClient(
        session=async_get_clientsession(hass),
        api_key=entry.data[CONF_API_KEY],
        host=entry.data.get(CONF_HOST, DEFAULT_HOST),
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = client

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
            image_bytes = await hass.async_add_executor_job(_read_image_file, image_path)
            filename = image_path.rsplit("/", 1)[-1] if "/" in image_path else image_path

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

    hass.services.async_register(
        DOMAIN,
        SERVICE_DIAGNOSE,
        handle_diagnose,
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
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
