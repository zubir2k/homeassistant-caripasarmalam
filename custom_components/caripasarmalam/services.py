"""Service actions for CariPasarMalam."""
from __future__ import annotations

import logging
from typing import Any

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

from .const import DEFAULT_HOME_RADIUS, DOMAIN, MAX_RADIUS, MIN_RADIUS
from .coordinator import CariPasarMalamCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_NEARBY = "get_nearby"

ATTR_ENTITY_ID = "entity_id"
ATTR_RADIUS = "radius"
ATTR_DAY = "day"
ATTR_LIMIT = "limit"

GET_NEARBY_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_ENTITY_ID, "target"): cv.entity_id,
        vol.Inclusive(ATTR_LATITUDE, "coords"): cv.latitude,
        vol.Inclusive(ATTR_LONGITUDE, "coords"): cv.longitude,
        vol.Optional(ATTR_RADIUS, default=DEFAULT_HOME_RADIUS): vol.All(
            vol.Coerce(float), vol.Range(min=MIN_RADIUS, max=MAX_RADIUS)
        ),
        vol.Optional(ATTR_DAY, default="today"): vol.In(
            ["today", "tomorrow", "mon", "tue", "wed", "thu", "fri", "sat", "sun", "all"]
        ),
        vol.Optional(ATTR_LIMIT, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=50)
        ),
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register CariPasarMalam services."""

    async def _handle_get_nearby(call: ServiceCall) -> ServiceResponse:
        """Handle get_nearby service call."""
        data = call.data
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError("CariPasarMalam integration is not loaded.")

        coordinator: CariPasarMalamCoordinator = entries[0].runtime_data
        if not coordinator:
            raise ServiceValidationError("CariPasarMalam coordinator is not initialized.")

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

        radius_km = float(data.get(ATTR_RADIUS, DEFAULT_HOME_RADIUS))
        day_filter = str(data.get(ATTR_DAY, "today"))
        limit = int(data.get(ATTR_LIMIT, 10))

        markets = coordinator.find_nearby_markets(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            day_filter=day_filter,
            limit=limit,
        )

        return {
            "count": len(markets),
            "requested_day": day_filter,
            "radius_km": radius_km,
            "latitude": lat,
            "longitude": lon,
            "nearest": markets[0] if markets else None,
            "markets": markets,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NEARBY,
        _handle_get_nearby,
        schema=GET_NEARBY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister CariPasarMalam services."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_NEARBY):
        hass.services.async_remove(DOMAIN, SERVICE_GET_NEARBY)
