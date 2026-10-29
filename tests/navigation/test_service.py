from datetime import datetime, timedelta, timezone

import pytest

from app.navigation.service import NavigationService


def test_location_is_stored():
    service = NavigationService()
    reading, alert = service.update_location(13.0827, 80.2707)

    assert reading.latitude == 13.0827
    assert reading.longitude == 80.2707
    assert service.latest_location == reading
    assert alert is None


def test_invalid_coordinates_are_rejected():
    service = NavigationService()

    with pytest.raises(ValueError):
        service.update_location(91, 80)

    with pytest.raises(ValueError):
        service.update_location(13, 181)


def test_safe_zone_rejects_invalid_radius():
    service = NavigationService()

    with pytest.raises(ValueError):
        service.set_safe_zone(13.0827, 80.2707, 0)


def test_location_inside_safe_zone_does_not_alert():
    service = NavigationService()
    service.set_safe_zone(13.0827, 80.2707, 200)

    _, alert = service.update_location(13.0827, 80.2707)

    assert alert is None


def test_leaving_safe_zone_generates_alert():
    service = NavigationService()
    service.set_safe_zone(13.0827, 80.2707, 100)

    _, alert = service.update_location(13.0827, 80.2707)
    assert alert is None

    _, alert = service.update_location(13.0927, 80.2707)

    assert alert is not None
    assert "exited" in alert.message
    assert alert.distance_metres > 100


def test_same_exit_does_not_generate_repeated_alerts():
    service = NavigationService()
    service.set_safe_zone(13.0827, 80.2707, 100)

    _, first_alert = service.update_location(13.0927, 80.2707)
    _, second_alert = service.update_location(13.0930, 80.2707)

    assert first_alert is not None
    assert second_alert is None


def test_returning_inside_allows_a_new_exit_alert():
    service = NavigationService()
    service.set_safe_zone(13.0827, 80.2707, 100)

    _, first_alert = service.update_location(13.0927, 80.2707)
    service.update_location(13.0827, 80.2707)
    _, second_alert = service.update_location(13.0927, 80.2707)

    assert first_alert is not None
    assert second_alert is not None


def test_older_location_reading_is_rejected():
    service = NavigationService()
    now = datetime.now(timezone.utc)

    service.update_location(13.0827, 80.2707, now)

    with pytest.raises(ValueError):
        service.update_location(
            13.0828, 80.2708, now - timedelta(seconds=10)
        )


def test_stale_location_is_detected():
    service = NavigationService()
    now = datetime.now(timezone.utc)

    assert service.is_location_stale(now=now)

    service.update_location(
        13.0827, 80.2707, now - timedelta(seconds=180)
    )

    assert service.is_location_stale(max_age_seconds=120, now=now)
    assert not service.is_location_stale(max_age_seconds=300, now=now)


def test_timestamp_must_include_timezone():
    service = NavigationService()

    with pytest.raises(ValueError):
        service.update_location(
            13.0827,
            80.2707,
            datetime(2026, 10, 29, 10, 0, 0),
        )
