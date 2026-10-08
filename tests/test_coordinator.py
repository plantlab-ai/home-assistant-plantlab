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
