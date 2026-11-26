"""Service actions for Cari Pasar Malam."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import voluptuous as vol

from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    DEFAULT_MAX_MARKETS,
    DEFAULT_RADIUS,
    DOMAIN,
    MAX_MAX_MARKETS,
    MAX_RADIUS,
    MIN_MAX_MARKETS,
    MIN_RADIUS,
    OPENING_SOON_MINUTES,
)
from .coordinator import CariPasarMalamCoordinator
from .markets import nearby

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_NEARBY = "get_nearby"

ATTR_ENTITY_ID = "entity_id"
ATTR_RADIUS = "radius"
ATTR_LIMIT = "limit"

GET_NEARBY_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_ENTITY_ID, "target"): cv.entity_id,
        vol.Inclusive(ATTR_LATITUDE, "coords"): cv.latitude,
        vol.Inclusive(ATTR_LONGITUDE, "coords"): cv.longitude,
        vol.Optional(ATTR_RADIUS, default=DEFAULT_RADIUS): vol.All(
            vol.Coerce(float), vol.Range(min=MIN_RADIUS, max=MAX_RADIUS)
        ),
        vol.Optional(ATTR_LIMIT, default=DEFAULT_MAX_MARKETS): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_MAX_MARKETS, max=MAX_MAX_MARKETS)
        ),
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Cari Pasar Malam services."""

    async def _handle_get_nearby(call: ServiceCall) -> ServiceResponse:
        """Handle get_nearby service call."""
        data = call.data
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError("Cari Pasar Malam integration is not loaded.")

        coordinator: CariPasarMalamCoordinator = entries[0].runtime_data
        if not coordinator:
            raise ServiceValidationError("Cari Pasar Malam coordinator is not initialized.")

        # Determine coordinates
        if ATTR_LATITUDE in data and ATTR_LONGITUDE in data:
            lat = float(data[ATTR_LATITUDE])
            lon = float(data[ATTR_LONGITUDE])
        else:
            entity_id = data.get(ATTR_ENTITY_ID, "zone.home")
            state = hass.states.get(entity_id)
            if state is None or ATTR_LATITUDE not in state.attributes or ATTR_LONGITUDE not in state.attributes:
                raise ServiceValidationError(
                    f"Entity '{entity_id}' has no GPS latitude and longitude."
                )
            lat = float(state.attributes[ATTR_LATITUDE])
            lon = float(state.attributes[ATTR_LONGITUDE])

        radius_km = float(data.get(ATTR_RADIUS, DEFAULT_RADIUS))
        limit = int(data.get(ATTR_LIMIT, DEFAULT_MAX_MARKETS))

        res = nearby(
            coordinator.markets,
            lat,
            lon,
            radius_km,
            limit,
            datetime.now(timezone.utc),
            OPENING_SOON_MINUTES,
        )

        return {
            "count": res.get("total", 0),
            "open_count": res.get("open_count", 0),
            "today_count": res.get("today_count", 0),
            "radius_km": radius_km,
            "latitude": lat,
            "longitude": lon,
            "nearest": res.get("featured"),
            "markets": res.get("markets", []),
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NEARBY,
        _handle_get_nearby,
        schema=GET_NEARBY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister Cari Pasar Malam services."""
    hass.services.async_remove(DOMAIN, SERVICE_GET_NEARBY)
