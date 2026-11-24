"""The CariPasarMalam integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .card_registration import async_register_card, async_unregister_card
from .const import DOMAIN
from .coordinator import CariPasarMalamConfigEntry, CariPasarMalamCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static path and bundled Lovelace card resource."""
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> bool:
    """Set up CariPasarMalam from a config entry."""
    await async_register_card(hass)

    coordinator = CariPasarMalamCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Set up actions / services
    async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> None:
    """Reload when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Check if there are other entries remaining
        remaining = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if not remaining:
            async_unload_services(hass)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> None:
    """Clean up stored cache and unregister card when the config entry is removed."""
    remaining = [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not remaining:
        await async_unregister_card(hass)
        if hasattr(entry, "runtime_data") and entry.runtime_data is not None:
            await entry.runtime_data._store.async_remove()
