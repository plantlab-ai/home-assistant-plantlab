"""The problem sensor must not fire on images that were never assessed."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.plantlab.sensor import SIGNAL_DIAGNOSIS_UPDATE

from .conftest import (
    DIAGNOSE_RESPONSE_HEALTHY,
    DIAGNOSE_RESPONSE_OUT_OF_SCOPE,
    DIAGNOSE_RESPONSE_TOMATO_HEALTHY,
    DIAGNOSE_RESPONSE_TOMATO_UNHEALTHY_UNNAMED,
    DIAGNOSE_RESPONSE_UNHEALTHY,
)


async def _setup(hass, mock_config_entry, mock_api_client):
    with patch(
        "custom_components.plantlab.PlantLabApiClient",
        return_value=mock_api_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


async def _state_after(hass, payload):
    async_dispatcher_send(hass, SIGNAL_DIAGNOSIS_UPDATE, payload)
    await hass.async_block_till_done()
    return hass.states.get("binary_sensor.plantlab_problem").state


async def test_unhealthy_cannabis_reports_a_problem(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)
    assert await _state_after(hass, DIAGNOSE_RESPONSE_UNHEALTHY) == "on"


async def test_healthy_cannabis_reports_no_problem(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)
    assert await _state_after(hass, DIAGNOSE_RESPONSE_HEALTHY) == "off"


async def test_out_of_scope_reports_unknown_not_a_problem(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)
    assert await _state_after(hass, DIAGNOSE_RESPONSE_OUT_OF_SCOPE) == "unknown"


async def test_healthy_tomato_reports_no_problem(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)
    assert await _state_after(hass, DIAGNOSE_RESPONSE_TOMATO_HEALTHY) == "off"


async def test_unhealthy_tomato_without_named_cause_reports_a_problem(
    hass: HomeAssistant, mock_config_entry, mock_api_client
):
    await _setup(hass, mock_config_entry, mock_api_client)
    assert await _state_after(hass, DIAGNOSE_RESPONSE_TOMATO_UNHEALTHY_UNNAMED) == "on"
