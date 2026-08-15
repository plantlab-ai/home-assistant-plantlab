def test_non_cannabis_history_items_are_not_counted_as_unhealthy():
    """A Stage-1A exit has no health verdict.

    /history reports is_healthy as a plain bool, so a non-cannabis diagnosis
    reads `false` there. Counting it filed every photo of a pot, a lamp or a
    pet under "unhealthy" in the 24h stats.
    """
    from datetime import UTC, datetime

    from custom_components.plantlab.coordinator import _compute_history_data

    now = datetime.now(tz=UTC).isoformat()
    items = [
        {"created_at": now, "is_cannabis": True, "is_healthy": True},
        {"created_at": now, "is_cannabis": True, "is_healthy": False},
        {"created_at": now, "is_cannabis": False, "is_healthy": False},
    ]
    data = _compute_history_data(items)

    assert data.healthy_count_24h == 1
    assert data.unhealthy_count_24h == 1, "the non-cannabis item must not count"
    assert data.count_24h == 3, "it is still a diagnosis that happened"


def test_history_without_is_cannabis_still_counts():
    """Older payloads omit the field; absence must not silently drop them."""
    from datetime import UTC, datetime

    from custom_components.plantlab.coordinator import _compute_history_data

    now = datetime.now(tz=UTC).isoformat()
    data = _compute_history_data([{"created_at": now, "is_healthy": False}])
    assert data.unhealthy_count_24h == 1
