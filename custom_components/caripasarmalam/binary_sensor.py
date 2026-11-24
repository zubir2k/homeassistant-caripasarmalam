"""Binary sensor platform for CariPasarMalam."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up CariPasarMalam binary sensors."""
    coordinator: CariPasarMalamCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []

    locations = coordinator.data.get("locations", {}) if coordinator.data else {}

    for target_id, loc_data in locations.items():
        target_name = loc_data.get("name", target_id)
        entities.append(
            PasarMalamOpenTonightBinarySensor(coordinator, target_id, target_name)
        )

    async_add_entities(entities)


class PasarMalamOpenTonightBinarySensor(CariPasarMalamEntity, BinarySensorEntity):
    """Binary sensor indicating whether any pasar malam is open tonight within radius."""

    _attr_translation_key = "open_tonight"

    def __init__(
        self,
        coordinator: CariPasarMalamCoordinator,
        target_id: str,
        target_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, target_id, target_name)
        clean_target = target_id.replace(".", "_")
        self._attr_unique_id = f"{clean_target}_open_tonight"

    @property
    def is_on(self) -> bool:
        """Return True if at least one market is scheduled today within radius."""
        data = self.location_data
        return bool(data.get("open_tonight", False))

    @property
    def icon(self) -> str:
        """Return dynamic store icon."""
        return "mdi:store-check" if self.is_on else "mdi:store-remove"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes describing the evening's markets."""
        data = self.location_data
        nearest = data.get("nearest_market_today") or {}
        return {
            "target": self._target_id,
            "target_name": self._target_name,
            "radius_km": data.get("radius_km"),
            "total_markets_today": data.get("open_today_count", 0),
            "open_now_count": data.get("open_now_count", 0),
            "nearest_market_name": nearest.get("name"),
            "nearest_market_distance_km": nearest.get("distance_km"),
            "nearest_market_status": nearest.get("status"),
            "nearest_market_hours": nearest.get("operating_hours_today"),
            "nearest_market_address": nearest.get("address"),
            "nearest_market_gmaps": nearest.get("gmaps_link"),
        }
