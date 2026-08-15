from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sensor import SIGNAL_DIAGNOSIS_UPDATE, primary_plant


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([PlantLabProblemSensor(entry)])


class PlantLabProblemSensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._diagnosis_data: dict | None = None

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_problem"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "PlantLab",
            "manufacturer": "PlantLab AI",
        }

    @property
    def is_on(self) -> bool | None:
        if self._diagnosis_data is None:
            return None
        # Not cannabis means health was never assessed, not that a problem was
        # found. Before v1.0.167 the API sent is_healthy=false on that exit, so
        # `not is_healthy` reported a problem for a photo of a coffee mug.
        if not self._diagnosis_data.get("is_cannabis"):
            return None
        is_healthy = primary_plant(self._diagnosis_data).get("is_healthy")
        if is_healthy is None:
            return None
        return not is_healthy

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        plant = primary_plant(self._diagnosis_data)
        conditions = plant.get("conditions", [])
        pests = plant.get("pests", [])
        problems = [
            {"name": c.get("display_name", c.get("class_id")), "confidence": c.get("confidence"), "type": "condition"}
            for c in conditions
        ] + [
            {"name": p.get("display_name", p.get("class_id")), "confidence": p.get("confidence"), "type": "pest"}
            for p in pests
        ]
        return {"problems": problems, "count": len(problems)}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_DIAGNOSIS_UPDATE,
                self._handle_diagnosis_update,
            )
        )

    @callback
    def _handle_diagnosis_update(self, data: dict) -> None:
        self._diagnosis_data = data
        self.async_write_ha_state()
