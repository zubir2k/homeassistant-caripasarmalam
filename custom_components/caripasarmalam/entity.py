"""Base entity for Cari Pasar Malam."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import get_device_info
from .coordinator import CariPasarMalamCoordinator


class CariPasarMalamEntity(CoordinatorEntity[CariPasarMalamCoordinator]):
    """Named in the context of the Cari Pasar Malam service device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CariPasarMalamCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = get_device_info(coordinator.config_entry.entry_id)
