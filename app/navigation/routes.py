from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.navigation.service import NavigationService

router = APIRouter(prefix="/navigation", tags=["Outdoor Navigation"])

# Prototype state: stored in memory until the server restarts.
navigation_service = NavigationService()


class LocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp: Optional[datetime] = None


class SafeZoneRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_metres: float = Field(gt=0, le=100000)


def location_to_dict(reading):
    return {
        "latitude": reading.latitude,
        "longitude": reading.longitude,
        "timestamp": reading.timestamp,
    }


def safe_zone_to_dict(zone):
    return {
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "radius_metres": zone.radius_metres,
    }


def alert_to_dict(alert):
    if alert is None:
        return None

    return {
        "message": alert.message,
        "distance_metres": alert.distance_metres,
        "timestamp": alert.timestamp,
    }


@router.post("/location")
def submit_location(request: LocationRequest):
    """Receive a location reading from the outdoor navigation device."""
    try:
        reading, alert = navigation_service.update_location(
            latitude=request.latitude,
            longitude=request.longitude,
            timestamp=request.timestamp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "location": location_to_dict(reading),
        "alert": alert_to_dict(alert),
    }


@router.get("/location")
def get_latest_location():
    """Return the latest reading and whether it is stale."""
    reading = navigation_service.latest_location

    if reading is None:
        raise HTTPException(
            status_code=404,
            detail="No location has been received yet.",
        )

    return {
        "location": location_to_dict(reading),
        "is_stale": navigation_service.is_location_stale(),
    }


@router.put("/safe-zone")
def configure_safe_zone(request: SafeZoneRequest):
    """Configure the circular safe zone selected by the caregiver."""
    try:
        zone = navigation_service.set_safe_zone(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_metres=request.radius_metres,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"safe_zone": safe_zone_to_dict(zone)}


@router.get("/safe-zone")
def get_safe_zone():
    """Return the currently configured safe zone."""
    zone = navigation_service.safe_zone

    if zone is None:
        raise HTTPException(
            status_code=404,
            detail="No safe zone has been configured.",
        )

    return {"safe_zone": safe_zone_to_dict(zone)}


@router.get("/alerts/latest")
def get_latest_alert():
    """Return the most recent safe-zone exit alert."""
    alert = navigation_service.last_alert

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="No safe-zone exit alert has been recorded.",
        )

    return {"alert": alert_to_dict(alert)}
