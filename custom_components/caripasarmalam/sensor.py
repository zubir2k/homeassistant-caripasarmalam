"""Sensor platform for CariPasarMalam."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CariPasarMalamConfigEntry, CariPasarMalamCoordinator
from .entity import CariPasarMalamEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CariPasarMalamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CariPasarMalam sensors from a config entry."""
    coordinator: CariPasarMalamCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    locations = coordinator.data.get("locations", {}) if coordinator.data else {}

    for target_id, loc_data in locations.items():
        target_name = loc_data.get("name", target_id)
        entities.append(
            NearestMarketSensor(coordinator, target_id, target_name)
        )
        entities.append(
            MarketCountSensor(coordinator, target_id, target_name)
        )

    # Integration wide catalog sensor
    entities.append(CatalogCountSensor(coordinator))

    async_add_entities(entities)


class NearestMarketSensor(CariPasarMalamEntity, SensorEntity):
    """Sensor reporting the nearest pasar malam open today to this location."""

    _attr_translation_key = "nearest_market"
    _attr_icon = "mdi:store-marker"

    def __init__(
        self,
        coordinator: CariPasarMalamCoordinator,
        target_id: str,
        target_name: str,
    ) -> None:
        """Initialize the nearest market sensor."""
        super().__init__(coordinator, target_id, target_name)
        clean_target = target_id.replace(".", "_")
        self._attr_unique_id = f"{clean_target}_nearest_market"

    @property
    def native_value(self) -> str | None:
        """Return the name of the nearest market open today."""
        data = self.location_data
        if not data.get("has_coordinates", True):
            return "No GPS coordinates"
        nearest = data.get("nearest_market_today")
        if not nearest:
            return "None open today"
        return nearest.get("name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed attributes for the nearest market."""
        data = self.location_data
        nearest = data.get("nearest_market_today") or {}
        attrs: dict[str, Any] = {
            "target": self._target_id,
            "target_name": self._target_name,
            "radius_km": data.get("radius_km"),
            "open_today_count": data.get("open_today_count", 0),
            "open_now_count": data.get("open_now_count", 0),
        }

        if nearest:
            attrs.update({
                "market_id": nearest.get("id"),
                "distance_km": nearest.get("distance_km"),
                "status": nearest.get("status"),
                "operating_hours_today": nearest.get("operating_hours_today"),
                "closes_at": nearest.get("closes_at"),
                "next_open_at": nearest.get("next_open_at"),
                "address": nearest.get("address"),
                "district": nearest.get("district"),
                "state": nearest.get("state"),
                "parking_available": nearest.get("parking_available"),
                "parking_accessible": nearest.get("parking_accessible"),
                "parking_notes": nearest.get("parking_notes"),
                "has_toilet": nearest.get("has_toilet"),
                "has_prayer_room": nearest.get("has_prayer_room"),
                "gmaps_link": nearest.get("gmaps_link"),
                "latitude": nearest.get("latitude"),
                "longitude": nearest.get("longitude"),
            })

        # List of all markets open today within radius
        attrs["markets_today"] = [
            {
                "name": m.get("name"),
                "distance_km": m.get("distance_km"),
                "operating_hours": m.get("operating_hours_today"),
                "status": m.get("status"),
                "address": m.get("address"),
                "gmaps_link": m.get("gmaps_link"),
            }
            for m in data.get("markets_today", [])
        ]

        return attrs


class MarketCountSensor(CariPasarMalamEntity, SensorEntity):
    """Sensor showing how many pasar malam are operating today within radius."""

    _attr_translation_key = "markets_today_count"
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "markets"

    def __init__(
        self,
        coordinator: CariPasarMalamCoordinator,
        target_id: str,
        target_name: str,
    ) -> None:
        """Initialize the count sensor."""
        super().__init__(coordinator, target_id, target_name)
        clean_target = target_id.replace(".", "_")
        self._attr_unique_id = f"{clean_target}_markets_today_count"

    @property
    def native_value(self) -> int:
        """Return the count of markets open today."""
        data = self.location_data
        return data.get("open_today_count", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional metrics."""
        data = self.location_data
        return {
            "radius_km": data.get("radius_km"),
            "open_now_count": data.get("open_now_count", 0),
            "total_nearby_all_days": len(data.get("all_nearby_markets", [])),
        }


class CatalogCountSensor(CariPasarMalamEntity, SensorEntity):
    """Diagnostic sensor reporting total markets in the local catalog."""

    _attr_translation_key = "catalog_count"
    _attr_icon = "mdi:database"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "markets"

    def __init__(self, coordinator: CariPasarMalamCoordinator) -> None:
        """Initialize the catalog count sensor."""
        super().__init__(coordinator, "system", "System")
        self._attr_unique_id = "caripasarmalam_total_catalog"

    @property
    def native_value(self) -> int:
        """Return count of markets in database."""
        return len(self.coordinator.markets)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return catalog metadata."""
        return {
            "last_catalog_update": (
                self.coordinator.last_catalog_update.isoformat()
                if self.coordinator.last_catalog_update
                else None
            ),
        }
