from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

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


async def test_sensors_after_healthy_diagnosis(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, DIAGNOSE_RESPONSE_HEALTHY)
    await hass.async_block_till_done()

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


async def test_reliability_score_zero_value(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """Zero reliability should show 0.0, not unknown."""
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    data = {**DIAGNOSE_RESPONSE_HEALTHY, "reliability_score": 0.0}
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, data)
    await hass.async_block_till_done()

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability.state == "0.0"
    assert reliability.attributes["reliability_label"] == "low_confidence"


async def test_reliability_score_missing_remains_unknown(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """When the API omits reliability_score (e.g., Stage 2 didn't run), the sensor stays unknown."""
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    data = {k: v for k, v in DIAGNOSE_RESPONSE_HEALTHY.items() if k != "reliability_score"}
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, data)
    await hass.async_block_till_done()

    reliability = hass.states.get("sensor.plantlab_reliability_score")
    assert reliability.state == "unknown"
    assert reliability.attributes["reliability_label"] is None
