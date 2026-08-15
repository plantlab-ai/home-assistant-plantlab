"""The problem sensor must not fire on images that were never assessed."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.plantlab.sensor import SIGNAL_DIAGNOSIS_UPDATE

from .conftest import (
    DIAGNOSE_RESPONSE_HEALTHY,
    DIAGNOSE_RESPONSE_NOT_CANNABIS,
    DIAGNOSE_RESPONSE_NOT_CANNABIS_LEGACY,
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


async def test_not_cannabis_reports_unknown_not_a_problem(hass: HomeAssistant, mock_config_entry, mock_api_client):
    """Stage 1A rejected the image, so health was never assessed."""
    await _setup(hass, mock_config_entry, mock_api_client)
    assert await _state_after(hass, DIAGNOSE_RESPONSE_NOT_CANNABIS) == "unknown"


async def test_not_cannabis_on_a_pre_1_0_167_api_is_still_not_a_problem(
    hass: HomeAssistant, mock_config_entry, mock_api_client
):
    """The regression this guard exists for.

    Before v1.0.167 the API sent is_healthy=false on a Stage-1A exit, so
    `not is_healthy` turned a photo of a coffee mug into "problem detected".
    """
    await _setup(hass, mock_config_entry, mock_api_client)
    assert await _state_after(hass, DIAGNOSE_RESPONSE_NOT_CANNABIS_LEGACY) == "unknown"
