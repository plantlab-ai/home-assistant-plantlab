from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.plantlab.api import PlantLabAuthError, PlantLabTierError
from custom_components.plantlab.coordinator import (
    HISTORY_POLL_INTERVAL,
    TIER_DENIED_POLL_INTERVAL,
    HistoryCoordinator,
)


def test_history_counts_health_only_for_items_that_carry_it():
    from datetime import UTC, datetime

    from custom_components.plantlab.coordinator import _compute_history_data

    now = datetime.now(tz=UTC).isoformat()
    items = [
        {"created_at": now, "species": "cannabis", "is_healthy": True},
        {"created_at": now, "species": "tomato", "is_healthy": False},
        {"created_at": now, "species": "tomato", "is_healthy": True},
        {"created_at": now, "species": None},
    ]
    data = _compute_history_data(items)
    assert data.count_24h == 4
    assert data.healthy_count_24h == 2
    assert data.unhealthy_count_24h == 1


async def test_history_auth_error_starts_reauth(hass, mock_config_entry):
    client = AsyncMock()
    client.async_get_history.side_effect = PlantLabAuthError("Invalid API key")
    coordinator = HistoryCoordinator(hass, mock_config_entry, client)

    assert coordinator.config_entry is mock_config_entry
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_history_tier_denial_backs_off_and_success_restores_polling(hass, mock_config_entry):
    client = AsyncMock()
    client.async_get_history.side_effect = PlantLabTierError("Tier unavailable")
    coordinator = HistoryCoordinator(hass, mock_config_entry, client)

    unavailable = await coordinator._async_update_data()
    assert unavailable.tier_unavailable is True
    assert coordinator.update_interval == TIER_DENIED_POLL_INTERVAL
    assert coordinator._tier_unavailable_logged is True

    client.async_get_history.side_effect = None
    client.async_get_history.return_value = {"items": []}
    recovered = await coordinator._async_update_data()
    assert recovered.tier_unavailable is False
    assert coordinator.update_interval == HISTORY_POLL_INTERVAL
    assert coordinator._tier_unavailable_logged is False
