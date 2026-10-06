"""A suspected candidate is a weak signal and must not read as a detection."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.plantlab.sensor import SIGNAL_DIAGNOSIS_UPDATE

from .conftest import DIAGNOSE_RESPONSE_SUSPECTED_V4, DIAGNOSE_RESPONSE_UNHEALTHY_V4


async def _diagnose(hass, mock_config_entry, mock_api_client, payload):
    with patch("custom_components.plantlab.PlantLabApiClient", return_value=mock_api_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, payload)
    await hass.async_block_till_done()


async def test_suspected_condition_state_is_marked(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _diagnose(hass, mock_config_entry, mock_api_client, DIAGNOSE_RESPONSE_SUSPECTED_V4)

    conditions = hass.states.get("sensor.plantlab_conditions")
    assert conditions.state == "Suspected: Nitrogen Deficiency"
    assert conditions.attributes["suspected"] is True
    assert [c["suspected"] for c in conditions.attributes["conditions"]] == [True, True]
    assert hass.states.get("sensor.plantlab_health").state == "unhealthy"


async def test_suspected_candidates_keep_the_problem_sensor_on_and_flagged(
    hass: HomeAssistant, mock_config_entry, mock_api_client
):
    await _diagnose(hass, mock_config_entry, mock_api_client, DIAGNOSE_RESPONSE_SUSPECTED_V4)

    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem.state == "on"
    assert problem.attributes["suspected"] is True
    assert all(item["suspected"] for item in problem.attributes["problems"])


async def test_confident_detection_is_not_suspected(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _diagnose(hass, mock_config_entry, mock_api_client, DIAGNOSE_RESPONSE_UNHEALTHY_V4)

    conditions = hass.states.get("sensor.plantlab_conditions")
    assert conditions.state == "Nitrogen Deficiency"
    assert conditions.attributes["suspected"] is False
    assert conditions.attributes["conditions"][0]["suspected"] is False
    pests = hass.states.get("sensor.plantlab_pests")
    assert pests.state == "Spider Mites"
    assert pests.attributes["suspected"] is False
    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem.attributes["suspected"] is False


async def test_suspected_pest_state_is_marked(hass: HomeAssistant, mock_config_entry, mock_api_client):
    payload = {
        **DIAGNOSE_RESPONSE_UNHEALTHY_V4,
        "results": [
            {
                **DIAGNOSE_RESPONSE_UNHEALTHY_V4["results"][0],
                "pests": [
                    {"class_id": "spider_mites", "display_name": "Spider Mites", "confidence": 0.2, "suspected": True}
                ],
            }
        ],
    }
    await _diagnose(hass, mock_config_entry, mock_api_client, payload)

    pests = hass.states.get("sensor.plantlab_pests")
    assert pests.state == "Suspected: Spider Mites"
    assert pests.attributes["suspected"] is True
    assert hass.states.get("sensor.plantlab_conditions").attributes["suspected"] is False
    assert hass.states.get("binary_sensor.plantlab_problem").attributes["suspected"] is False
