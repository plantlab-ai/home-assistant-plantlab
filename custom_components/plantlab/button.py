from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CAMERA_ENTITY, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([PlantLabDiagnoseButton(entry)])


class PlantLabDiagnoseButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "diagnose"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_diagnose"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PlantLab",
            "manufacturer": "PlantLab AI",
        }

    async def async_press(self) -> None:
        from . import ENTRY_KEY_CLIENT, async_diagnose_camera

        camera_entity_id = self._entry.options.get(CONF_CAMERA_ENTITY)
        if not camera_entity_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_camera_selected",
            )
        client = self.hass.data[DOMAIN][self._entry.entry_id][ENTRY_KEY_CLIENT]
        await async_diagnose_camera(self.hass, client, camera_entity_id)
