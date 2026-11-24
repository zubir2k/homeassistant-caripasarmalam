"""Base entity for CariPasarMalam."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import CariPasarMalamCoordinator


class CariPasarMalamEntity(CoordinatorEntity[CariPasarMalamCoordinator]):
    """Defines a base CariPasarMalam entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CariPasarMalamCoordinator,
        target_id: str,
        target_name: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._target_id = target_id
        self._target_name = target_name

    @property
    def location_data(self) -> dict[str, Any]:
        """Get location data from coordinator."""
        if not self.coordinator.data or "locations" not in self.coordinator.data:
            return {}
        return self.coordinator.data["locations"].get(self._target_id, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this location tracker."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._target_id)},
            name=f"CariPasarMalam ({self._target_name})",
            manufacturer="CariPasarMalam",
            model="Night Market Proximity Tracker",
            sw_version=VERSION,
            configuration_url="https://pasarmalam.app",
        )
