"""Diagnostics for Cari Pasar Malam, with locations and person identities redacted."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import CariPasarMalamConfigEntry

TO_REDACT = {"latitude", "longitude", "origin", "name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CariPasarMalamConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry with personal details redacted."""
    c = entry.runtime_data
    raw_locations = (c.data or {}).get("locations", {})
    # Anonymize dictionary keys so individual household member names are not exposed in dumps
    anonymized_locations = {
        ("home" if key == "zone.home" else f"person_{idx}"): async_redact_data(val, TO_REDACT)
        for idx, (key, val) in enumerate(raw_locations.items())
    }

    return {
        "options": dict(entry.options),
        "last_update_success": c.last_update_success,
        "dataset_fetched": c.fetched.isoformat() if c.fetched else None,
        "markets_raw": c.raw_count,
        "markets_usable": len(c.markets),
        "markets_without_schedule": sum(1 for m in c.markets if not m.sessions),
        "last_error": c.last_error,
        "locations": anonymized_locations,
    }
