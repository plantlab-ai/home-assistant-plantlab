import copy
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.plantlab.api import PlantLabTierError
from custom_components.plantlab.sensor import SIGNAL_DIAGNOSIS_UPDATE

from .conftest import (
    DIAGNOSE_RESPONSE_HEALTHY,
    DIAGNOSE_RESPONSE_NOT_CANNABIS,
    DIAGNOSE_RESPONSE_UNHEALTHY,
)


async def _setup_integration(hass, mock_config_entry, mock_api_client):
    with patch(
        "custom_components.plantlab.PlantLabApiClient",
        return_value=mock_api_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


async def test_sensors_initial_state(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    health = hass.states.get("sensor.plantlab_health")
    assert health is not None
    assert health.state == "unknown"

    conditions = hass.states.get("sensor.plantlab_conditions")
    assert conditions is not None
    assert conditions.state == "unknown"

    pests = hass.states.get("sensor.plantlab_pests")
    assert pests is not None
    assert pests.state == "unknown"

    growth = hass.states.get("sensor.plantlab_growth_stage")
    assert growth is not None
    assert growth.state == "unknown"

    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem is not None
    assert problem.state == "unknown"

    nutrient = hass.states.get("sensor.plantlab_nutrient_analysis")
    assert nutrient is not None
    assert nutrient.state == "unknown"

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability is not None
    assert reliability.state == "unknown"

    engine_version = hass.states.get("sensor.plantlab_engine_version")
    assert engine_version is not None
    assert engine_version.state == "unknown"

    plant_count = hass.states.get("sensor.plantlab_plant_count")
    assert plant_count is not None
    assert plant_count.state == "unknown"


async def test_sensors_after_healthy_diagnosis(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, DIAGNOSE_RESPONSE_HEALTHY)
    await hass.async_block_till_done()

    engine_version = hass.states.get("sensor.plantlab_engine_version")
    assert engine_version.state == "1.0.93"
    assert engine_version.attributes["models"] == "v3"

    plant_count = hass.states.get("sensor.plantlab_plant_count")
    assert plant_count.state == "1"

    health = hass.states.get("sensor.plantlab_health")
    assert health.state == "healthy"
    assert health.attributes["confidence"] == 0.95
    assert health.attributes["is_cannabis"] is True

    conditions = hass.states.get("sensor.plantlab_conditions")
    assert conditions.state == "none"
    assert conditions.attributes["count"] == 0
    assert conditions.attributes["reliability_score"] == 0.95

    pests = hass.states.get("sensor.plantlab_pests")
    assert pests.state == "none"
    assert pests.attributes["count"] == 0
    assert pests.attributes["reliability_score"] == 0.95

    growth = hass.states.get("sensor.plantlab_growth_stage")
    assert growth.state == "flowering"
    assert growth.attributes["confidence"] == 0.92

    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem.state == "off"

    nutrient = hass.states.get("sensor.plantlab_nutrient_analysis")
    assert nutrient.state == "none"
    assert nutrient.attributes["count"] == 0

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability.state == "95.0"
    assert reliability.attributes["reliability_label"] == "confident"
    assert reliability.attributes["uncertainty_factors"] == []


async def test_sensors_after_unhealthy_diagnosis(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, DIAGNOSE_RESPONSE_UNHEALTHY)
    await hass.async_block_till_done()

    health = hass.states.get("sensor.plantlab_health")
    assert health.state == "unhealthy"

    conditions = hass.states.get("sensor.plantlab_conditions")
    assert conditions.state == "Nitrogen Deficiency"
    assert conditions.attributes["count"] == 1
    assert conditions.attributes["conditions"][0]["name"] == "Nitrogen Deficiency"
    assert conditions.attributes["conditions"][0]["confidence"] == 0.85
    assert conditions.attributes["reliability_score"] == 0.82

    pests = hass.states.get("sensor.plantlab_pests")
    assert pests.state == "Spider Mites"
    assert pests.attributes["count"] == 1
    assert pests.attributes["reliability_score"] == 0.82

    growth = hass.states.get("sensor.plantlab_growth_stage")
    assert growth.state == "vegetative"

    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem.state == "on"
    assert problem.attributes["count"] == 2

    nutrient = hass.states.get("sensor.plantlab_nutrient_analysis")
    assert nutrient.state == "potassium_excess"
    assert nutrient.attributes["count"] == 2
    assert nutrient.attributes["hypotheses"][0]["excess"] == "potassium_excess"
    assert nutrient.attributes["hypotheses"][0]["explains"] == ["nitrogen_deficiency"]
    assert nutrient.attributes["hypotheses"][0]["evidence"] == 0.85
    assert nutrient.attributes["hypotheses"][0]["evidence_count"] == 1

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability.state == "82.0"
    assert reliability.attributes["reliability_label"] == "confident"


async def test_sensors_after_not_cannabis(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, DIAGNOSE_RESPONSE_NOT_CANNABIS)
    await hass.async_block_till_done()

    health = hass.states.get("sensor.plantlab_health")
    assert health.state == "not_cannabis"
    assert health.attributes["is_cannabis"] is False

    conditions = hass.states.get("sensor.plantlab_conditions")
    assert conditions.state == "none"
    assert conditions.attributes["count"] == 0

    pests = hass.states.get("sensor.plantlab_pests")
    assert pests.state == "none"
    assert pests.attributes["count"] == 0

    growth = hass.states.get("sensor.plantlab_growth_stage")
    assert growth.state == "unknown"

    nutrient = hass.states.get("sensor.plantlab_nutrient_analysis")
    assert nutrient.state == "none"
    assert nutrient.attributes["count"] == 0

    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem.state == "unknown"

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability.state == "unknown"

    plant_count = hass.states.get("sensor.plantlab_plant_count")
    assert plant_count.state == "0"


async def test_sensors_multi_plant_surfaces_primary(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """With more than one detected plant, plant_count reflects the total and
    the per-plant sensors surface the primary (first) plant."""
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    data = copy.deepcopy(DIAGNOSE_RESPONSE_UNHEALTHY)
    second_plant = copy.deepcopy(data["results"][0])
    second_plant["is_healthy"] = True
    second_plant["bbox"] = {"x0": 0.5, "y0": 0.0, "x1": 1.0, "y1": 1.0, "normalized": True}
    second_plant["conditions"] = []
    second_plant["pests"] = []
    data["results"].append(second_plant)

    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, data)
    await hass.async_block_till_done()

    plant_count = hass.states.get("sensor.plantlab_plant_count")
    assert plant_count.state == "2"

    # Primary (results[0]) is the unhealthy plant — sensors track it.
    health = hass.states.get("sensor.plantlab_health")
    assert health.state == "unhealthy"

    conditions = hass.states.get("sensor.plantlab_conditions")
    assert conditions.state == "Nitrogen Deficiency"

    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem.state == "on"


async def test_reliability_score_zero_value(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """Zero reliability should show 0.0, not unknown."""
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    data = copy.deepcopy(DIAGNOSE_RESPONSE_HEALTHY)
    data["results"][0]["reliability_score"] = 0.0
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, data)
    await hass.async_block_till_done()

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability.state == "0.0"
    assert reliability.attributes["reliability_label"] == "low_confidence"


async def test_reliability_score_missing_remains_unknown(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """When the API omits reliability_score (e.g., Stage 2 didn't run), the sensor stays unknown."""
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    data = copy.deepcopy(DIAGNOSE_RESPONSE_HEALTHY)
    data["results"][0].pop("reliability_score", None)
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, data)
    await hass.async_block_till_done()

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability.state == "unknown"
    assert reliability.attributes["reliability_label"] is None


async def test_engine_version_missing_remains_unknown(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """When the API omits engine_version (older server), the sensor stays unknown."""
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    data = {k: v for k, v in DIAGNOSE_RESPONSE_HEALTHY.items() if k != "engine_version"}
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, data)
    await hass.async_block_till_done()

    engine_version = hass.states.get("sensor.plantlab_engine_version")
    assert engine_version.state == "unknown"


async def test_engine_version_partial_models_missing(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """If only api populates (e.g., manifest lacks model_iterations), state shows api and models attribute is None."""
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    data = {**DIAGNOSE_RESPONSE_HEALTHY, "engine_version": {"api": "1.0.93", "models": ""}}
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, data)
    await hass.async_block_till_done()

    engine_version = hass.states.get("sensor.plantlab_engine_version")
    assert engine_version.state == "1.0.93"
    assert engine_version.attributes["models"] in (None, "")


# ---------------------------------------------------------------------------
# History activity sensor tests
# ---------------------------------------------------------------------------

# Freeze time at a moment where the first two HISTORY_RESPONSE items (timestamps
# ending in T10:00 and T09:00 on 2026-05-08) fall within 24h, and the third
# (2026-05-01) falls outside 24h but within 7d.
_FROZEN_NOW = "2026-05-08T12:00:00+00:00"


def _make_history_response(items: list[dict]) -> dict:
    return {"items": items, "count": len(items), "next_cursor": ""}


def _item(*, created_at: str, is_healthy: bool | None = True) -> dict:
    return {
        "id": "x",
        "request_id": "r",
        "class_id": "healthy" if is_healthy else "nitrogen_deficiency",
        "confidence": 0.9,
        "is_cannabis": True,
        "is_healthy": is_healthy,
        "conditions": [],
        "pests": [],
        "engine_version": "1.0.94",
        "created_at": created_at,
    }


@freeze_time(_FROZEN_NOW)
async def test_history_sensor_state_24h_count(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """Sensor state equals count of items with created_at within the last 24h."""
    now = datetime.fromisoformat(_FROZEN_NOW)
    within_24h = (now - timedelta(hours=1)).isoformat()
    within_24h_2 = (now - timedelta(hours=12)).isoformat()
    within_24h_3 = (now - timedelta(hours=23)).isoformat()
    outside_24h = (now - timedelta(hours=25)).isoformat()
    outside_24h_2 = (now - timedelta(days=3)).isoformat()

    items = [
        _item(created_at=within_24h),
        _item(created_at=within_24h_2),
        _item(created_at=within_24h_3),
        _item(created_at=outside_24h),
        _item(created_at=outside_24h_2),
    ]
    mock_api_client.async_get_history = AsyncMock(return_value=_make_history_response(items))

    await _setup_integration(hass, mock_config_entry, mock_api_client)
    await hass.async_block_till_done()

    sensor = hass.states.get("sensor.plantlab_diagnosis_activity")
    assert sensor is not None
    assert sensor.state == "3"


@freeze_time(_FROZEN_NOW)
async def test_history_sensor_attributes_healthy_split(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """healthy_count_24h and unhealthy_count_24h reflect the is_healthy split for 24h items."""
    now = datetime.fromisoformat(_FROZEN_NOW)
    within_24h = (now - timedelta(hours=2)).isoformat()

    items = [
        _item(created_at=within_24h, is_healthy=True),
        _item(created_at=within_24h, is_healthy=True),
        _item(created_at=within_24h, is_healthy=False),
    ]
    mock_api_client.async_get_history = AsyncMock(return_value=_make_history_response(items))

    await _setup_integration(hass, mock_config_entry, mock_api_client)
    await hass.async_block_till_done()

    sensor = hass.states.get("sensor.plantlab_diagnosis_activity")
    assert sensor.state == "3"
    assert sensor.attributes["healthy_count_24h"] == 2
    assert sensor.attributes["unhealthy_count_24h"] == 1
    assert sensor.attributes["count_7d"] == 3
    assert sensor.attributes["tier_unavailable"] is False


@freeze_time(_FROZEN_NOW)
async def test_history_sensor_403_tier_unavailable(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """When API returns 403, state=0, tier_unavailable=True, no exception raised."""
    mock_api_client.async_get_history = AsyncMock(side_effect=PlantLabTierError("free tier"))

    await _setup_integration(hass, mock_config_entry, mock_api_client)
    await hass.async_block_till_done()

    sensor = hass.states.get("sensor.plantlab_diagnosis_activity")
    assert sensor is not None
    assert sensor.state == "0"
    assert sensor.attributes["tier_unavailable"] is True


@freeze_time(_FROZEN_NOW)
async def test_history_sensor_empty_response(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """When API returns 200 with empty items list, state=0 and last_diagnosed_at is absent."""
    mock_api_client.async_get_history = AsyncMock(return_value=_make_history_response([]))

    await _setup_integration(hass, mock_config_entry, mock_api_client)
    await hass.async_block_till_done()

    sensor = hass.states.get("sensor.plantlab_diagnosis_activity")
    assert sensor is not None
    assert sensor.state == "0"
    assert "last_diagnosed_at" not in sensor.attributes
    assert sensor.attributes["tier_unavailable"] is False


def test_history_sensor_translation_keys():
    """strings.json, en.json and de.json all contain the history_activity sensor keys."""
    import json
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    integration_dir = repo_root / "custom_components" / "plantlab"

    required_keys = {
        "entity.sensor.history_activity.name",
        "entity.sensor.history_activity.state_attributes.healthy_count_24h.name",
        "entity.sensor.history_activity.state_attributes.unhealthy_count_24h.name",
        "entity.sensor.history_activity.state_attributes.count_7d.name",
        "entity.sensor.history_activity.state_attributes.last_diagnosed_at.name",
        "entity.sensor.history_activity.state_attributes.tier_unavailable.name",
    }

    def leaf_paths(data: dict, prefix: str = "") -> set[str]:
        paths: set[str] = set()
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                paths.update(leaf_paths(value, path))
            else:
                paths.add(path)
        return paths

    for fname in ("strings.json", "translations/en.json", "translations/de.json"):
        catalog = json.loads((integration_dir / fname).read_text())
        missing = required_keys - leaf_paths(catalog)
        assert not missing, f"{fname} is missing keys: {missing}"
