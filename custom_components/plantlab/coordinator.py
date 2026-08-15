from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .api import PlantLabApiClient, PlantLabConnectionError, PlantLabTierError

_LOGGER = logging.getLogger(__name__)

HISTORY_POLL_INTERVAL = timedelta(minutes=30)
_HISTORY_FETCH_WINDOW = timedelta(days=7)
_HISTORY_FETCH_LIMIT = 1000


class HistoryData:
    """Aggregated metrics computed from a /history response."""

    __slots__ = (
        "count_7d",
        "count_24h",
        "healthy_count_24h",
        "last_diagnosed_at",
        "tier_unavailable",
        "unhealthy_count_24h",
    )

    def __init__(
        self,
        *,
        count_24h: int,
        healthy_count_24h: int,
        unhealthy_count_24h: int,
        count_7d: int,
        last_diagnosed_at: str | None,
        tier_unavailable: bool,
    ) -> None:
        self.count_24h = count_24h
        self.healthy_count_24h = healthy_count_24h
        self.unhealthy_count_24h = unhealthy_count_24h
        self.count_7d = count_7d
        self.last_diagnosed_at = last_diagnosed_at
        self.tier_unavailable = tier_unavailable

    @classmethod
    def unavailable(cls) -> HistoryData:
        return cls(
            count_24h=0,
            healthy_count_24h=0,
            unhealthy_count_24h=0,
            count_7d=0,
            last_diagnosed_at=None,
            tier_unavailable=True,
        )

    @classmethod
    def empty(cls) -> HistoryData:
        return cls(
            count_24h=0,
            healthy_count_24h=0,
            unhealthy_count_24h=0,
            count_7d=0,
            last_diagnosed_at=None,
            tier_unavailable=False,
        )


def _compute_history_data(items: list[dict]) -> HistoryData:
    now = datetime.now(tz=UTC)
    cutoff_24h = now - timedelta(hours=24)

    count_24h = 0
    healthy_24h = 0
    unhealthy_24h = 0
    last_at: str | None = None

    for item in items:
        created_at_str = item.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            continue

        if last_at is None or created_at_str > last_at:
            last_at = created_at_str

        if created_at >= cutoff_24h:
            count_24h += 1
            # A non-cannabis diagnosis carries no health verdict: the cascade
            # exits at Stage 1A before health runs. /history still reports
            # is_healthy as a plain bool, so it reads `false` there -- counting
            # it would file every photo of a pot, a lamp or a pet under
            # "unhealthy". /diagnose omits the field entirely from v1.0.167.
            if not item.get("is_cannabis", True):
                continue
            if item.get("is_healthy") is True:
                healthy_24h += 1
            elif item.get("is_healthy") is False:
                unhealthy_24h += 1

    return HistoryData(
        count_24h=count_24h,
        healthy_count_24h=healthy_24h,
        unhealthy_count_24h=unhealthy_24h,
        count_7d=len(items),
        last_diagnosed_at=last_at,
        tier_unavailable=False,
    )


class HistoryCoordinator(DataUpdateCoordinator[HistoryData]):
    """Coordinator that polls /history every 30 minutes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: PlantLabApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="PlantLab history",
            update_interval=HISTORY_POLL_INTERVAL,
        )
        self._client = client
        self._tier_unavailable_logged = False

    async def _async_update_data(self) -> HistoryData:
        since = (datetime.now(tz=UTC) - _HISTORY_FETCH_WINDOW).isoformat()
        try:
            payload = await self._client.async_get_history(since_iso=since, limit=_HISTORY_FETCH_LIMIT)
        except PlantLabTierError:
            if not self._tier_unavailable_logged:
                _LOGGER.info(
                    "PlantLab history not available (free tier or training opt-in disabled). "
                    "Sensor will report tier_unavailable=true."
                )
                self._tier_unavailable_logged = True
            return HistoryData.unavailable()
        except PlantLabConnectionError as err:
            # Leave previous state; coordinator raises UpdateFailed which keeps prior data on retry
            raise UpdateFailed(f"Error fetching PlantLab history: {err}") from err

        items: list[dict] = payload.get("items", [])
        if not items:
            return HistoryData.empty()
        return _compute_history_data(items)
