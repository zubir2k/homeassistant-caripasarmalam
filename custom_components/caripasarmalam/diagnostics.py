"""Diagnostics for Cari Pasar Malam, with locations redacted."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import CariPasarMalamConfigEntry

TO_REDACT = {"latitude", "longitude", "origin", "name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CariPasarMalamConfigEntry
) -> dict[str, Any]:
    c = entry.runtime_data
    return {
        "options": dict(entry.options),
        "last_update_success": c.last_update_success,
        "dataset_fetched": c.fetched.isoformat() if c.fetched else None,
        "markets_raw": c.raw_count,
        "markets_usable": len(c.markets),
        "markets_without_schedule": sum(1 for m in c.markets if not m.sessions),
        "last_error": c.last_error,
        "locations": async_redact_data((c.data or {}).get("locations", {}), TO_REDACT),
    }
