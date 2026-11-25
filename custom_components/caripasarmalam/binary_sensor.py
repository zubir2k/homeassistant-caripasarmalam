"""Binary sensor: whether any pasar malam is open today/tonight within radius."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import (
    CONF_MAX_MARKETS,
    CONF_RADIUS,
    DEFAULT_MAX_MARKETS,
    DEFAULT_RADIUS,
    HOME,
    OPENING_SOON_MINUTES,
)
from .coordinator import CariPasarMalamConfigEntry, CariPasarMalamCoordinator
from .entity import CariPasarMalamEntity
from .markets import nearby

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

PREFIX = "pasarmalam_"
SUFFIX = "_open_tonight"
HOME_UID = f"pasarmalam_home{SUFFIX}"


def _uid(source: str) -> str:
    return HOME_UID if source == HOME else f"{PREFIX}{source.split('.', 1)[1]}{SUFFIX}"


async def async_setup_entry(
    hass: HomeAssistant, entry: CariPasarMalamConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    added: set[str] = set()

    @callback
    def _sync() -> None:
        if not coordinator.last_update_success or not coordinator.data:
            return
        locations = coordinator.data.get("locations", {})
        wanted = {_uid(s) for s in locations}
        new = []
        for source in sorted(locations):
            uid = _uid(source)
            if uid not in added:
                new.append(PasarMalamOpenTonightBinarySensor(coordinator, source))
                added.add(uid)
        if new:
            async_add_entities(new)

        ent_reg = er.async_get(hass)
        for reg in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            uid = reg.unique_id
            if reg.domain != "binary_sensor" or uid in wanted or not uid.startswith(PREFIX):
                continue
            _LOGGER.info("Removing %s: location no longer tracked", reg.entity_id)
            ent_reg.async_remove(reg.entity_id)
            added.discard(uid)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class PasarMalamOpenTonightBinarySensor(CariPasarMalamEntity, BinarySensorEntity):
    """Binary sensor on if any pasar malam is scheduled today or currently open within radius."""

    _unrecorded_attributes = frozenset({"markets_today", "featured", "origin", "radius_km"})

    def __init__(self, coordinator: CariPasarMalamCoordinator, source: str) -> None:
        super().__init__(coordinator)
        self._source = source
        uid = _uid(source)
        self._attr_unique_id = uid
        self.entity_id = f"binary_sensor.{uid}"
        if source == HOME:
            self._attr_translation_key = "home_open_tonight"
        else:
            self._attr_translation_key = "person_open_tonight"
            st = coordinator.hass.states.get(source)
            name = st.attributes.get("friendly_name") if st else None
            self._attr_translation_placeholders = {"person": name or source.split(".", 1)[1]}

        opts = coordinator.config_entry.options
        self._radius = float(opts.get(CONF_RADIUS, DEFAULT_RADIUS))
        self._limit = int(opts.get(CONF_MAX_MARKETS, DEFAULT_MAX_MARKETS))
        self._result: dict | None = None
        self._origin: tuple[float, float] | None = None

    def _coords(self) -> tuple[float, float] | None:
        st = self.hass.states.get(self._source)
        if st is None:
            return None
        lat, lon = st.attributes.get("latitude"), st.attributes.get("longitude")
        if lat is None or lon is None:
            return None
        try:
            return float(lat), float(lon)
        except (TypeError, ValueError):
            return None

    def _recompute(self) -> None:
        coords = self._coords()
        markets = self.coordinator.markets
        if coords is None or not markets:
            self._result, self._origin = None, coords
            return
        self._origin = coords
        self._result = nearby(
            markets, coords[0], coords[1], self._radius, self._limit,
            datetime.now(timezone.utc), OPENING_SOON_MINUTES,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._recompute()

        @callback
        def _tick(_now=None) -> None:
            self._recompute()
            self.async_write_ha_state()

        @callback
        def _moved(event: Event[EventStateChangedData]) -> None:
            old, new = event.data["old_state"], event.data["new_state"]
            if new is None:
                return
            if old is not None and (
                old.attributes.get("latitude"), old.attributes.get("longitude")
            ) == (new.attributes.get("latitude"), new.attributes.get("longitude")):
                return
            _tick()

        self.async_on_remove(async_track_time_interval(self.hass, _tick, timedelta(minutes=1)))
        self.async_on_remove(async_track_state_change_event(self.hass, [self._source], _moved))

    @callback
    def _handle_coordinator_update(self) -> None:
        self._recompute()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return super().available and self._result is not None

    @property
    def is_on(self) -> bool:
        if not self._result:
            return False
        return (self._result.get("today_count", 0) > 0) or (self._result.get("open_count", 0) > 0)

    @property
    def icon(self) -> str:
        return "mdi:store-check" if self.is_on else "mdi:store-remove"

    @property
    def extra_state_attributes(self) -> dict:
        r = self._result or {}
        featured = r.get("featured")
        today_markets = [m for m in r.get("markets", []) if m.get("today")]
        return {
            "source": self._source,
            "origin": list(self._origin) if self._origin else None,
            "radius_km": self._radius,
            "today_count": r.get("today_count", 0),
            "open_count": r.get("open_count", 0),
            "featured": featured["name"] if featured else None,
            "featured_status": featured["status"] if featured else None,
            "markets_today": [
                {
                    "name": m["name"],
                    "hours": m.get("today", []),
                    "distance_km": m["distance_km"],
                    "status": m["status"],
                }
                for m in today_markets
            ],
            "attribution": "Data: CariPasarMalam (pasarmalam.app), community maintained",
        }
