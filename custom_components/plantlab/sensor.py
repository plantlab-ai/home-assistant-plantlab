from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HistoryCoordinator, HistoryData

SIGNAL_DIAGNOSIS_UPDATE = f"{DOMAIN}_diagnosis_update"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    from . import ENTRY_KEY_HISTORY_COORDINATOR

    history_coordinator: HistoryCoordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_KEY_HISTORY_COORDINATOR]

    async_add_entities(
        [
            PlantLabHealthSensor(entry),
            PlantLabConditionsSensor(entry),
            PlantLabPestsSensor(entry),
            PlantLabGrowthStageSensor(entry),
            PlantLabNutrientAnalysisSensor(entry),
            PlantLabReliabilityScoreSensor(entry),
            PlantLabCoarseFallbackSensor(entry),
            PlantLabPlantCountSensor(entry),
            PlantLabEngineVersionSensor(entry),
            PlantLabHistoryActivitySensor(entry, history_coordinator),
        ]
    )


def primary_plant(data: dict | None) -> dict:
    """The first detected plant in a schema 3.0.0 diagnose response.

    PlantLab returns one diagnosis per detected plant under ``results``; the
    sensors here surface the first (primary) plant. An empty ``results`` (a
    not-cannabis image) yields an empty dict. A pre-3.0.0 payload had no
    ``results`` key and carried the per-plant fields at the top level, so the
    whole dict is returned as a fallback — this keeps an updated integration
    working against an as-yet-unupgraded API during a staged rollout."""
    if not data:
        return {}
    results = data.get("results")
    if isinstance(results, list):
        if results and isinstance(results[0], dict):
            return results[0]
        return {}
    return data


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
        is_healthy = primary_plant(self._diagnosis_data).get("is_healthy")
        if is_healthy is None:
            return None
        return "healthy" if is_healthy else "unhealthy"

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        return {
            "confidence": primary_plant(self._diagnosis_data).get("health_confidence"),
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
        conditions = primary_plant(self._diagnosis_data).get("conditions", [])
        if not conditions:
            return "none"
        return conditions[0].get("display_name", conditions[0].get("class_id", "unknown"))

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        plant = primary_plant(self._diagnosis_data)
        conditions = plant.get("conditions", [])
        return {
            "conditions": [
                {
                    "name": c.get("display_name", c.get("class_id")),
                    "confidence": c.get("confidence"),
                    "coarse_group": c.get("coarse_group"),
                }
                for c in conditions
            ],
            "count": len(conditions),
            "reliability_score": plant.get("reliability_score"),
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
        pests = primary_plant(self._diagnosis_data).get("pests", [])
        if not pests:
            return "none"
        return pests[0].get("display_name", pests[0].get("class_id", "unknown"))

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        plant = primary_plant(self._diagnosis_data)
        pests = plant.get("pests", [])
        return {
            "pests": [
                {
                    "name": p.get("display_name", p.get("class_id")),
                    "confidence": p.get("confidence"),
                    "coarse_group": p.get("coarse_group"),
                }
                for p in pests
            ],
            "count": len(pests),
            "reliability_score": plant.get("reliability_score"),
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
        return primary_plant(self._diagnosis_data).get("growth_stage")

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        return {
            "confidence": primary_plant(self._diagnosis_data).get("growth_stage_confidence"),
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
        score = primary_plant(self._diagnosis_data).get("reliability_score")
        if score is None:
            return None
        return round(score * 100, 1)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        plant = primary_plant(self._diagnosis_data)
        score = plant.get("reliability_score")
        return {
            "reliability_label": _reliability_label(score),
            "uncertainty_factors": plant.get("uncertainty_factors", []),
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
        hypotheses = primary_plant(self._diagnosis_data).get("mulders_hypotheses", [])
        if not hypotheses:
            return "none"
        return hypotheses[0].get("excess", "unknown")

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        hypotheses = primary_plant(self._diagnosis_data).get("mulders_hypotheses", [])
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


class PlantLabCoarseFallbackSensor(PlantLabBaseSensor):
    """Clinical coarse group for the primary plant when the specific (fine-class)
    diagnosis is below the API's confidence threshold (schema 3.1.0
    ``coarse_fallback``). State is the group key (e.g. ``mobile_nutrient``) or
    ``none`` when the API was confident enough to assert a specific class. Lets a
    dashboard or automation react when the diagnosis is only reliable at the
    group level rather than surfacing a confidently-wrong specific label."""

    _attr_translation_key = "coarse_fallback"
    _attr_icon = "mdi:help-circle-outline"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_coarse_fallback"

    @property
    def native_value(self) -> str | None:
        if self._diagnosis_data is None:
            return None
        return primary_plant(self._diagnosis_data).get("coarse_fallback") or "none"


class PlantLabPlantCountSensor(PlantLabBaseSensor):
    """Number of distinct plants the last diagnosis detected (schema 3.0.0).

    State is ``len(results)``; the per-plant sensors surface the first plant.
    A not-cannabis image reports 0. Marked diagnostic — it informs users when
    the frame held more than one plant (only the primary is broken out)."""

    _attr_translation_key = "plant_count"
    _attr_icon = "mdi:sprout-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_plant_count"

    @property
    def native_value(self) -> int | None:
        if self._diagnosis_data is None:
            return None
        results = self._diagnosis_data.get("results")
        if not isinstance(results, list):
            return None
        return len(results)


class PlantLabEngineVersionSensor(PlantLabBaseSensor):
    """Reports the API build + global model iteration that served the last
    diagnosis. Marked diagnostic so it groups under HA's diagnostic entities
    rather than cluttering the main dashboard. State carries the API build
    (e.g. "1.0.93"); the model iteration label is exposed as the `models`
    attribute (e.g. "v3"). Lets automations detect engine upgrades."""

    _attr_translation_key = "engine_version"
    _attr_icon = "mdi:cog-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_engine_version"

    @property
    def native_value(self) -> str | None:
        if self._diagnosis_data is None:
            return None
        engine = self._diagnosis_data.get("engine_version")
        if not isinstance(engine, dict):
            return None
        api = engine.get("api")
        return api or None

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._diagnosis_data is None:
            return None
        engine = self._diagnosis_data.get("engine_version")
        if not isinstance(engine, dict):
            return {"models": None}
        return {"models": engine.get("models")}


_HISTORY_POLL_INTERVAL_MINUTES = 30


class PlantLabHistoryActivitySensor(CoordinatorEntity[HistoryCoordinator], SensorEntity):
    """Polls /history every 30 minutes and reports diagnosis activity metrics.

    State: count of diagnoses in the last 24 hours.
    Attributes expose healthy/unhealthy split for 24h, total 7d count,
    most-recent timestamp, and a flag when the endpoint is unavailable
    (free tier or training opt-in disabled).
    """

    _attr_translation_key = "history_activity"
    _attr_icon = "mdi:history"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, coordinator: HistoryCoordinator) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_history_activity"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "PlantLab",
            "manufacturer": "PlantLab AI",
        }

    @property
    def native_value(self) -> int:
        data: HistoryData | None = self.coordinator.data
        if data is None:
            return 0
        return data.count_24h

    @property
    def extra_state_attributes(self) -> dict:
        data: HistoryData | None = self.coordinator.data
        if data is None:
            return {"tier_unavailable": False}
        attrs: dict = {
            "healthy_count_24h": data.healthy_count_24h,
            "unhealthy_count_24h": data.unhealthy_count_24h,
            "count_7d": data.count_7d,
            "tier_unavailable": data.tier_unavailable,
        }
        if data.last_diagnosed_at is not None:
            attrs["last_diagnosed_at"] = data.last_diagnosed_at
        return attrs
