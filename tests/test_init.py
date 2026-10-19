from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.plantlab.api import PlantLabAuthError
from custom_components.plantlab.const import DOMAIN, SERVICE_DIAGNOSE
from custom_components.plantlab.coordinator import HISTORY_POLL_INTERVAL


async def test_setup_entry(hass: HomeAssistant, mock_config_entry, mock_api_client):
    with patch(
        "custom_components.plantlab.PlantLabApiClient",
        return_value=mock_api_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert hass.services.has_service(DOMAIN, SERVICE_DIAGNOSE)


async def test_unload_entry(hass: HomeAssistant, mock_config_entry, mock_api_client):
    with patch(
        "custom_components.plantlab.PlantLabApiClient",
        return_value=mock_api_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN not in hass.data
    assert not hass.services.has_service(DOMAIN, SERVICE_DIAGNOSE)


async def test_invalid_key_during_first_history_refresh_starts_reauth(hass, mock_config_entry):
    with patch("custom_components.plantlab.PlantLabApiClient") as mock_cls:
        mock_cls.return_value.async_get_history = AsyncMock(side_effect=PlantLabAuthError("Invalid API key"))
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    progress = hass.config_entries.flow.async_progress()
    assert len(progress) == 1
    assert progress[0]["context"]["source"] == config_entries.SOURCE_REAUTH
    assert progress[0]["context"]["entry_id"] == mock_config_entry.entry_id
    assert DOMAIN not in hass.data


async def test_runtime_history_auth_error_starts_one_reauth_and_stops_polling(
    hass, mock_config_entry, mock_api_client
):
    with patch("custom_components.plantlab.PlantLabApiClient", return_value=mock_api_client):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["history_coordinator"]
        assert coordinator._unsub_refresh is not None
        assert mock_api_client.async_get_history.await_count == 1

        mock_api_client.async_get_history.side_effect = PlantLabAuthError("Invalid API key")
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    progress = hass.config_entries.flow.async_progress()
    assert len(progress) == 1
    assert progress[0]["context"]["source"] == config_entries.SOURCE_REAUTH
    assert progress[0]["context"]["entry_id"] == mock_config_entry.entry_id
    assert coordinator._unsub_refresh is None
    assert coordinator.update_interval == HISTORY_POLL_INTERVAL
    assert mock_api_client.async_get_history.await_count == 2
