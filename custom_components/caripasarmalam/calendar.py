"""Calendar platform: weekly schedules of nearby pasar malam as calendar events."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_RADIUS,
    DEFAULT_RADIUS,
    HOME,
)
from .coordinator import CariPasarMalamConfigEntry, CariPasarMalamCoordinator
from .entity import CariPasarMalamEntity
from .markets import Market, haversine_km

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

MYT = ZoneInfo("Asia/Kuala_Lumpur")

PREFIX = "pasarmalam_"
SUFFIX = "_calendar"
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
                new.append(PasarMalamCalendarEntity(coordinator, source))
                added.add(uid)
        if new:
            async_add_entities(new)

        ent_reg = er.async_get(hass)
        for reg in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            uid = reg.unique_id
            if reg.domain != "calendar" or uid in wanted or not uid.startswith(PREFIX):
                continue
            _LOGGER.info("Removing %s: location no longer tracked", reg.entity_id)
            ent_reg.async_remove(reg.entity_id)
            added.discard(uid)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class PasarMalamCalendarEntity(CariPasarMalamEntity, CalendarEntity):
    """Calendar entity showing nearby night market schedules."""

    def __init__(self, coordinator: CariPasarMalamCoordinator, source: str) -> None:
        super().__init__(coordinator)
        self._source = source
        uid = _uid(source)
        self._attr_unique_id = uid
        self.entity_id = f"calendar.{uid.removesuffix(SUFFIX)}"
        if source == HOME:
            self._attr_translation_key = "home_calendar"
        else:
            self._attr_translation_key = "person_calendar"
            st = coordinator.hass.states.get(source)
            name = st.attributes.get("friendly_name") if st else None
            self._attr_translation_placeholders = {"person": name or source.split(".", 1)[1]}

        opts = coordinator.config_entry.options
        self._radius = float(opts.get(CONF_RADIUS, DEFAULT_RADIUS))
        self._nearby_markets: list[tuple[float, Market]] = []

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
            self._nearby_markets = []
            return
        found = []
        for mk in markets:
            dist = haversine_km(coords[0], coords[1], mk.lat, mk.lon)
            if dist <= self._radius and mk.sessions:
                found.append((dist, mk))
        found.sort(key=lambda x: x[0])
        self._nearby_markets = found

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._recompute()

        @callback
        def _moved(event: Event[EventStateChangedData]) -> None:
            old, new = event.data["old_state"], event.data["new_state"]
            if new is None:
                return
            if old is not None and (
                old.attributes.get("latitude"), old.attributes.get("longitude")
            ) == (new.attributes.get("latitude"), new.attributes.get("longitude")):
                return
            self._recompute()
            self.async_write_ha_state()

        self.async_on_remove(async_track_state_change_event(self.hass, [self._source], _moved))

    @callback
    def _handle_coordinator_update(self) -> None:
        self._recompute()
        super()._handle_coordinator_update()

    def _events_between(self, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        if not self._nearby_markets:
            return events

        local_start = start_date.astimezone(MYT)
        local_end = end_date.astimezone(MYT)

        cur_day = local_start.date()
        end_day = local_end.date()

        while cur_day <= end_day:
            weekday = cur_day.weekday()
            day_midnight = datetime(cur_day.year, cur_day.month, cur_day.day, 0, 0, tzinfo=MYT)

            for dist, mk in self._nearby_markets:
                for s_start, s_end in mk.sessions:
                    if s_start // 1440 == weekday:
                        m_start = s_start % 1440
                        duration = s_end - s_start
                        ev_start = day_midnight + timedelta(minutes=m_start)
                        ev_end = ev_start + timedelta(minutes=duration)

                        if ev_end > local_start and ev_start < local_end:
                            amenities = []
                            if mk.parking:
                                amenities.append("Parking")
                            if mk.prayer_room:
                                amenities.append("Surau")
                            if mk.toilet:
                                amenities.append("Toilet")

                            desc = (
                                f"Distance: {dist:.1f} km\n"
                                f"Address: {mk.address}\n"
                                f"District: {mk.district}, {mk.state}\n"
                                f"Amenities: {', '.join(amenities) if amenities else 'None'}"
                            )

                            events.append(
                                CalendarEvent(
                                    start=ev_start,
                                    end=ev_end,
                                    summary=f"Pasar Malam {mk.name}",
                                    description=desc,
                                    location=mk.address or f"{mk.lat},{mk.lon}",
                                    uid=f"{mk.id}_{cur_day.strftime('%Y%m%d')}_{m_start}",
                                )
                            )

            cur_day += timedelta(days=1)

        events.sort(key=lambda ev: ev.start)
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next or ongoing event."""
        now = datetime.now(MYT)
        events = self._events_between(now, now + timedelta(days=7))
        return events[0] if events else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return self._events_between(start_date, end_date)
