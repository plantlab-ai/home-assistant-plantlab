from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

SIGNAL_DIAGNOSIS_UPDATE = f"{DOMAIN}_diagnosis_update"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            PlantLabHealthSensor(entry),
            PlantLabConditionsSensor(entry),
            PlantLabPestsSensor(entry),
            PlantLabGrowthStageSensor(entry),
            PlantLabNutrientAnalysisSensor(entry),
            PlantLabReliabilityScoreSensor(entry),
        ]
    )


# Reliability label thresholds. Stage 2 emits a continuous score in [0, 1];
# the categorical attribute is for users who want a simple bucket in dashboards.
_RELIABILITY_CONFIDENT_MIN = 0.7
_RELIABILITY_UNCERTAIN_MIN = 0.3


def _reliability_label(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= _RELIABILITY_CONFIDENT_MIN:
        return "confident"
    if score >= _RELIABILITY_UNCERTAIN_MIN:
        return "uncertain"
    return "low_confidence"


class PlantLabBaseSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._diagnosis_data: dict | None = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "PlantLab",
            "manufacturer": "PlantLab AI",
        }

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


class PlantLabHealthSensor(PlantLabBaseSensor):
    _attr_translation_key = "health"
    _attr_icon = "mdi:leaf"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_health"

    @property
    def native_value(self) -> str | None:
        if self._diagnosis_data is None:
            return None
        if not self._diagnosis_data.get("is_cannabis"):
            return "not_cannabis"
        is_healthy = self._diagnosis_data.get("is_healthy")
        if is_healthy is None:
            return None
        return "healthy" if is_healthy else "unhealthy"

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        return {
            "confidence": self._diagnosis_data.get("health_confidence"),
            "is_cannabis": self._diagnosis_data.get("is_cannabis"),
            "cannabis_confidence": self._diagnosis_data.get("cannabis_confidence"),
        }


class PlantLabConditionsSensor(PlantLabBaseSensor):
    _attr_translation_key = "conditions"
    _attr_icon = "mdi:alert-circle-outline"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_conditions"

    @property
    def native_value(self) -> str | None:
        if self._diagnosis_data is None:
            return None
        conditions = self._diagnosis_data.get("conditions", [])
        if not conditions:
            return "none"
        return conditions[0].get("display_name", conditions[0].get("class_id", "unknown"))

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        conditions = self._diagnosis_data.get("conditions", [])
        return {
            "conditions": [
                {"name": c.get("display_name", c.get("class_id")), "confidence": c.get("confidence")}
                for c in conditions
            ],
            "count": len(conditions),
            "reliability_score": self._diagnosis_data.get("reliability_score"),
        }


class PlantLabPestsSensor(PlantLabBaseSensor):
    _attr_translation_key = "pests"
    _attr_icon = "mdi:bug-outline"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_pests"

    @property
    def native_value(self) -> str | None:
        if self._diagnosis_data is None:
            return None
        pests = self._diagnosis_data.get("pests", [])
        if not pests:
            return "none"
        return pests[0].get("display_name", pests[0].get("class_id", "unknown"))

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        pests = self._diagnosis_data.get("pests", [])
        return {
            "pests": [
                {"name": p.get("display_name", p.get("class_id")), "confidence": p.get("confidence")} for p in pests
            ],
            "count": len(pests),
            "reliability_score": self._diagnosis_data.get("reliability_score"),
        }


class PlantLabGrowthStageSensor(PlantLabBaseSensor):
    _attr_translation_key = "growth_stage"
    _attr_icon = "mdi:sprout"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_growth_stage"

    @property
    def native_value(self) -> str | None:
        if self._diagnosis_data is None:
            return None
        return self._diagnosis_data.get("growth_stage")

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        return {
            "confidence": self._diagnosis_data.get("growth_stage_confidence"),
        }


class PlantLabReliabilityScoreSensor(PlantLabBaseSensor):
    _attr_translation_key = "reliability_score"
    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = "%"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_reliability_score"

    @property
    def native_value(self) -> float | None:
        if self._diagnosis_data is None:
            return None
        score = self._diagnosis_data.get("reliability_score")
        if score is None:
            return None
        return round(score * 100, 1)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        score = self._diagnosis_data.get("reliability_score")
        return {
            "reliability_label": _reliability_label(score),
            "uncertainty_factors": self._diagnosis_data.get("uncertainty_factors", []),
        }


class PlantLabNutrientAnalysisSensor(PlantLabBaseSensor):
    _attr_translation_key = "nutrient_analysis"
    _attr_icon = "mdi:flask-outline"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_nutrient_analysis"

    @property
    def native_value(self) -> str | None:
        if self._diagnosis_data is None:
            return None
        hypotheses = self._diagnosis_data.get("mulders_hypotheses", [])
        if not hypotheses:
            return "none"
        return hypotheses[0].get("excess", "unknown")

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        hypotheses = self._diagnosis_data.get("mulders_hypotheses", [])
        return {
            "hypotheses": [
                {
                    "excess": h.get("excess"),
                    "explains": h.get("explains", []),
                    "evidence": h.get("evidence"),
                    "evidence_count": h.get("evidence_count"),
                }
                for h in hypotheses
            ],
            "count": len(hypotheses),
        }
