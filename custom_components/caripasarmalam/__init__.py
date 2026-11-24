"""Cari Pasar Malam: nearby pasar malam for your home and everyone with GPS."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .card_registration import async_register_card, async_unregister_card
from .const import DOMAIN
from .coordinator import CariPasarMalamConfigEntry, CariPasarMalamCoordinator, cache_store
from .services import async_setup_services, async_unload_services

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve and register the bundled map card."""
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> bool:
    """Set up from a config entry."""
    await async_register_card(hass)

    coordinator = CariPasarMalamCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        remaining = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if not remaining:
            async_unload_services(hass)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the card resource and cached dataset when the integration is deleted."""
    others = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]
    if not others:
        await async_unregister_card(hass)
        await cache_store(hass).async_remove()
