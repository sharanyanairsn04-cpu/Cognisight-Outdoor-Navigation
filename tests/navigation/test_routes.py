
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.navigation import routes as navigation_routes
from app.navigation.service import NavigationService


@pytest.fixture(autouse=True)
def reset_navigation_service(monkeypatch):
    """Give each test a clean navigation state."""
    monkeypatch.setattr(
        navigation_routes,
        "navigation_service",
        NavigationService(),
    )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_submit_location(client):
    response = client.post(
        "/api/v1/navigation/location",
        json={"latitude": 13.0827, "longitude": 80.2707},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["location"]["latitude"] == pytest.approx(13.0827)
    assert data["location"]["longitude"] == pytest.approx(80.2707)
    assert data["alert"] is None


def test_get_latest_location(client):
    client.post(
        "/api/v1/navigation/location",
        json={"latitude": 13.0827, "longitude": 80.2707},
    )

    response = client.get("/api/v1/navigation/location")

    assert response.status_code == 200
    assert response.json()["is_stale"] is False


def test_location_not_found_before_first_reading(client):
    response = client.get("/api/v1/navigation/location")

    assert response.status_code == 404


def test_configure_and_get_safe_zone(client):
    payload = {
        "latitude": 13.0827,
        "longitude": 80.2707,
        "radius_metres": 500,
    }

    response = client.put(
        "/api/v1/navigation/safe-zone",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["safe_zone"]["radius_metres"] == 500

    response = client.get("/api/v1/navigation/safe-zone")

    assert response.status_code == 200
    assert response.json()["safe_zone"]["latitude"] == pytest.approx(13.0827)


def test_invalid_safe_zone_is_rejected(client):
    response = client.put(
        "/api/v1/navigation/safe-zone",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "radius_metres": 0,
        },
    )

    assert response.status_code == 422


def test_exiting_safe_zone_generates_alert(client):
    client.put(
        "/api/v1/navigation/safe-zone",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "radius_metres": 500,
        },
    )

    response = client.post(
        "/api/v1/navigation/location",
        json={"latitude": 13.0927, "longitude": 80.2707},
    )

    assert response.status_code == 200
    alert = response.json()["alert"]
    assert alert is not None
    assert alert["message"] == "Patient has exited the safe zone."


def test_latest_alert_endpoint(client):
    client.put(
        "/api/v1/navigation/safe-zone",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "radius_metres": 500,
        },
    )

    client.post(
        "/api/v1/navigation/location",
        json={"latitude": 13.0927, "longitude": 80.2707},
    )

    response = client.get("/api/v1/navigation/alerts/latest")

    assert response.status_code == 200
    assert response.json()["alert"]["message"] == (
        "Patient has exited the safe zone."
    )
