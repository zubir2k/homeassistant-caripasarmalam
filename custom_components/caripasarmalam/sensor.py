"""Sensors: one per location (Home zone and each person with GPS), plus a dataset sensor."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
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
    MARKET_URL,
    OPENING_SOON_MINUTES,
)
from .coordinator import CariPasarMalamConfigEntry, CariPasarMalamCoordinator
from .entity import CariPasarMalamEntity
from .markets import nearby

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

PREFIX = "pasarmalam_"
DATASET_UID = "pasarmalam_dataset"
HOME_UID = "pasarmalam_home"


def _uid(source: str) -> str:
    return HOME_UID if source == HOME else f"{PREFIX}{source.split('.', 1)[1]}"


async def async_setup_entry(
    hass: HomeAssistant, entry: CariPasarMalamConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([DatasetSensor(coordinator)])

    # Same approach as eSolat GPS: a sensor for zone.home and one per person with GPS,
    # added when GPS appears and removed (via the registry) when it goes.
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
                new.append(LocationSensor(coordinator, source))
                added.add(uid)
        if new:
            async_add_entities(new)

        ent_reg = er.async_get(hass)
        for reg in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            uid = reg.unique_id
            if uid == DATASET_UID or uid in wanted or not uid.startswith(PREFIX):
                continue
            _LOGGER.info("Removing %s: location no longer tracked", reg.entity_id)
            ent_reg.async_remove(reg.entity_id)
            added.discard(uid)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class LocationSensor(CariPasarMalamEntity, SensorEntity):
    """Markets around one location. State: how many are open right now."""

    _attr_native_unit_of_measurement = "markets"
    # The market list changes every minute and is large; keep it out of the recorder.
    _unrecorded_attributes = frozenset(
        {"markets", "featured", "nearest_open", "next_opening", "origin", "radius_km", "dataset_updated"}
    )

    def __init__(self, coordinator: CariPasarMalamCoordinator, source: str) -> None:
        super().__init__(coordinator)
        self._source = source
        uid = _uid(source)
        self._attr_unique_id = uid
        self.entity_id = f"sensor.{uid}"
        if source == HOME:
            self._attr_translation_key = "home"
        else:
            self._attr_translation_key = "person"
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
    def native_value(self) -> int | None:
        return self._result["open_count"] if self._result else None

    @property
    def extra_state_attributes(self) -> dict:
        r = self._result or {}
        featured = r.get("featured")
        attrs = {
            "source": self._source,
            "origin": list(self._origin) if self._origin else None,
            "radius_km": self._radius,
            "featured": featured["name"] if featured else None,
            "featured_status": featured["status"] if featured else None,
            "nearby_count": r.get("total", 0),
            "opening_soon_count": r.get("opening_soon_count", 0),
            "today_count": r.get("today_count", 0),
            "nearest_open": r.get("nearest_open"),
            "next_opening": r.get("next_opening"),
            "markets": [
                {**m, "url": MARKET_URL.format(id=m["id"])} for m in r.get("markets", [])
            ],
            "dataset_updated": self.coordinator.fetched.isoformat() if self.coordinator.fetched else None,
            "attribution": "Data: CariPasarMalam (pasarmalam.app), community maintained",
        }
        return attrs


class DatasetSensor(CariPasarMalamEntity, SensorEntity):
    """Diagnostic: when the market dataset was last fetched and how much of it is usable."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "dataset"

    def __init__(self, coordinator: CariPasarMalamCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = DATASET_UID
        self.entity_id = "sensor.pasarmalam_dataset"

    @property
    def native_value(self):
        return self.coordinator.fetched

    @property
    def extra_state_attributes(self) -> dict:
        mk = self.coordinator.markets
        return {
            "markets": self.coordinator.raw_count,
            "usable": len(mk),
            "without_schedule": sum(1 for m in mk if not m.sessions),
            "last_error": self.coordinator.last_error,
        }
