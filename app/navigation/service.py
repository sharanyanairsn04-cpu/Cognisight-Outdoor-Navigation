from dataclasses import dataclass
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Optional


@dataclass(frozen=True)
class LocationReading:
    latitude: float
    longitude: float
    timestamp: datetime


@dataclass(frozen=True)
class SafeZone:
    latitude: float
    longitude: float
    radius_metres: float


@dataclass(frozen=True)
class GeofenceAlert:
    message: str
    distance_metres: float
    timestamp: datetime


class NavigationService:
    """In-memory location tracking and safe-zone monitoring."""

    EARTH_RADIUS_METRES = 6_371_000

    def __init__(self) -> None:
        self.latest_location: Optional[LocationReading] = None
        self.safe_zone: Optional[SafeZone] = None
        self.last_alert: Optional[GeofenceAlert] = None
        self._currently_outside: Optional[bool] = None

    @staticmethod
    def _validate_coordinates(latitude: float, longitude: float) -> None:
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90.")
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180.")

    @staticmethod
    def _validate_number(value: float, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number.")
        if not float("-inf") < float(value) < float("inf"):
            raise ValueError(f"{name} must be finite.")

    def set_safe_zone(
        self,
        latitude: float,
        longitude: float,
        radius_metres: float,
    ) -> SafeZone:
        self._validate_number(latitude, "Latitude")
        self._validate_number(longitude, "Longitude")
        self._validate_number(radius_metres, "Radius")
        self._validate_coordinates(latitude, longitude)

        if radius_metres <= 0:
            raise ValueError("Safe-zone radius must be greater than zero.")
        if radius_metres > 100_000:
            raise ValueError("Safe-zone radius cannot exceed 100000 metres.")

        self.safe_zone = SafeZone(
            latitude=float(latitude),
            longitude=float(longitude),
            radius_metres=float(radius_metres),
        )
        self._currently_outside = None
        self.last_alert = None
        return self.safe_zone

    @classmethod
    def distance_metres(
        cls,
        latitude1: float,
        longitude1: float,
        latitude2: float,
        longitude2: float,
    ) -> float:
        """Calculate the great-circle distance between two coordinates."""
        lat1, lon1, lat2, lon2 = map(
            radians, (latitude1, longitude1, latitude2, longitude2)
        )
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        a = (
            sin(delta_lat / 2) ** 2
            + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        )
        a = min(1.0, max(0.0, a))
        return cls.EARTH_RADIUS_METRES * 2 * asin(sqrt(a))

    def update_location(
        self,
        latitude: float,
        longitude: float,
        timestamp: Optional[datetime] = None,
    ) -> tuple[LocationReading, Optional[GeofenceAlert]]:
        self._validate_number(latitude, "Latitude")
        self._validate_number(longitude, "Longitude")
        self._validate_coordinates(latitude, longitude)

        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone.")

        if (
            self.latest_location is not None
            and timestamp < self.latest_location.timestamp
        ):
            raise ValueError("Location timestamp is older than the latest reading.")

        reading = LocationReading(
            latitude=float(latitude),
            longitude=float(longitude),
            timestamp=timestamp,
        )
        self.latest_location = reading

        new_alert = None
        if self.safe_zone is not None:
            zone = self.safe_zone
            distance = self.distance_metres(
                zone.latitude, zone.longitude, latitude, longitude
            )
            outside = distance > zone.radius_metres

            if outside and self._currently_outside is not True:
                new_alert = GeofenceAlert(
                    message="Patient has exited the safe zone.",
                    distance_metres=round(distance, 2),
                    timestamp=timestamp,
                )
                self.last_alert = new_alert

            self._currently_outside = outside

        return reading, new_alert

    def is_location_stale(
        self,
        max_age_seconds: float = 120,
        now: Optional[datetime] = None,
    ) -> bool:
        if max_age_seconds <= 0:
            raise ValueError("Maximum age must be greater than zero.")

        if self.latest_location is None:
            return True

        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Current time must include a timezone.")

        age = (now - self.latest_location.timestamp).total_seconds()
        return age < 0 or age > max_age_seconds
