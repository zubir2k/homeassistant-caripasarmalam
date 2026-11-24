"""Calendar platform for CariPasarMalam."""
from __future__ import annotations

from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MYT, WEEKDAY_CODES
from .coordinator import CariPasarMalamConfigEntry, CariPasarMalamCoordinator
from .entity import CariPasarMalamEntity
from .helpers import parse_time_to_minutes

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CariPasarMalamConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CariPasarMalam calendar entities."""
    coordinator: CariPasarMalamCoordinator = entry.runtime_data
    entities: list[CalendarEntity] = []

    locations = coordinator.data.get("locations", {}) if coordinator.data else {}

    for target_id, loc_data in locations.items():
        # Only create calendar for Home zone and persons with coordinates
        if not loc_data.get("has_coordinates", True):
            continue
        target_name = loc_data.get("name", target_id)
        entities.append(
            PasarMalamCalendarEntity(coordinator, target_id, target_name)
        )

    async_add_entities(entities)


class PasarMalamCalendarEntity(CariPasarMalamEntity, CalendarEntity):
    """Calendar entity displaying weekly schedules of nearby pasar malam."""

    _attr_translation_key = "market_calendar"
    _attr_icon = "mdi:calendar-star"

    def __init__(
        self,
        coordinator: CariPasarMalamCoordinator,
        target_id: str,
        target_name: str,
    ) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator, target_id, target_name)
        clean_target = target_id.replace(".", "_")
        self._attr_unique_id = f"{clean_target}_calendar"
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next or ongoing event."""
        now = datetime.now(MYT)
        events = self._get_events_between(now, now + timedelta(days=7))
        return events[0] if events else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return self._get_events_between(start_date, end_date)

    def _get_events_between(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Generate calendar events for all nearby markets within the date window."""
        events: list[CalendarEvent] = []
        loc_data = self.location_data
        nearby_markets = loc_data.get("all_nearby_markets", [])

        # Start from the start_date's beginning of day up to end_date
        current_dt = start_date.astimezone(MYT).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = end_date.astimezone(MYT)

        while current_dt <= end_dt:
            day_code = WEEKDAY_CODES.get(current_dt.weekday(), "mon")

            for market in nearby_markets:
                schedule = market.get("schedule", [])
                for rule in schedule:
                    if not isinstance(rule, dict):
                        continue
                    if day_code not in rule.get("days", []):
                        continue

                    times = rule.get("times", [])
                    for t in times:
                        start_str = t.get("start", "16:00")
                        end_str = t.get("end", "22:00")

                        start_min = parse_time_to_minutes(start_str)
                        end_min = parse_time_to_minutes(end_str)

                        event_start = current_dt.replace(
                            hour=start_min // 60,
                            minute=start_min % 60,
                        )

                        if end_min >= start_min:
                            event_end = current_dt.replace(
                                hour=end_min // 60,
                                minute=end_min % 60,
                            )
                        else:
                            # Cross midnight
                            event_end = (current_dt + timedelta(days=1)).replace(
                                hour=end_min // 60,
                                minute=end_min % 60,
                            )

                        # Filter against request bounds
                        if event_end < start_date or event_start > end_date:
                            continue

                        dist = market.get("distance_km")
                        dist_str = f"{dist} km away" if dist is not None else ""
                        parking_note = market.get("parking_notes") or ("Available" if market.get("parking_available") else "None")

                        description_parts = [
                            f"Distance: {dist_str}",
                            f"Operating Hours: {start_str} - {end_str}",
                            f"Parking: {parking_note}",
                            f"Toilet: {'Yes' if market.get('has_toilet') else 'No'} | Surau: {'Yes' if market.get('has_prayer_room') else 'No'}",
                        ]
                        if market.get("gmaps_link"):
                            description_parts.append(f"Directions: {market['gmaps_link']}")

                        events.append(
                            CalendarEvent(
                                start=event_start,
                                end=event_end,
                                summary=f"{market.get('name')} ({dist_str})" if dist_str else market.get("name"),
                                description="\n".join(description_parts),
                                location=market.get("address"),
                                uid=f"{market.get('id')}_{current_dt.strftime('%Y%m%d')}_{start_min}",
                            )
                        )

            current_dt += timedelta(days=1)

        events.sort(key=lambda ev: ev.start)
        return events
