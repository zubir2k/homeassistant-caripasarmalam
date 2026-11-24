"""Helper utilities for CariPasarMalam integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any

from .const import (
    MYT,
    OPENING_SOON_MINUTES,
    WEEKDAY_CODES,
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth (in km)."""
    r_earth = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(r_earth * c, 2)


def parse_time_to_minutes(time_str: str) -> int:
    """Parse 'HH:MM' string to minutes from start of day."""
    if not time_str or ":" not in time_str:
        return 0
    parts = time_str.split(":")
    try:
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return hours * 60 + minutes
    except (ValueError, IndexError):
        return 0


def get_market_open_status(market: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Calculate whether a market is currently open, opening soon, or closed.

    Returns dict with:
        status: 'open' | 'opening_soon' | 'closed'
        closes_at: datetime | None
        minutes_until_close: int | None
        next_open_at: datetime | None
        minutes_until_next_open: int | None
        today_times: list[dict]
    """
    local_now = now if now is not None else datetime.now(MYT)
    current_minutes = local_now.hour * 60 + local_now.minute
    current_weekday = local_now.weekday()  # 0=Mon, 6=Sun
    current_day_code = WEEKDAY_CODES.get(current_weekday, "mon")

    schedule = market.get("schedule", [])
    if not isinstance(schedule, list):
        schedule = []

    # Flatten schedule rules into day -> time ranges
    # ranges: list of (day_idx, start_minutes, end_minutes, note)
    ranges: list[tuple[int, int, int, str]] = []
    today_times: list[dict[str, Any]] = []

    for rule in schedule:
        if not isinstance(rule, dict):
            continue
        days = rule.get("days", [])
        times = rule.get("times", [])
        for d in days:
            # find day_idx from code
            day_idx = next((k for k, v in WEEKDAY_CODES.items() if v == d), None)
            if day_idx is None:
                continue
            for t in times:
                start_min = parse_time_to_minutes(t.get("start", ""))
                end_min = parse_time_to_minutes(t.get("end", ""))
                note = t.get("note", "")

                if d == current_day_code:
                    today_times.append({
                        "start": t.get("start", ""),
                        "end": t.get("end", ""),
                        "note": note,
                    })

                if end_min >= start_min:
                    ranges.append((day_idx, start_min, end_min, note))
                else:
                    # Cross-midnight slot (e.g. 18:00 -> 01:00)
                    ranges.append((day_idx, start_min, 24 * 60, note))
                    ranges.append(((day_idx + 1) % 7, 0, end_min, note))

    # 1. Check if open right now
    open_slots = [
        r for r in ranges
        if r[0] == current_weekday and r[1] <= current_minutes < r[2]
    ]

    if open_slots:
        # Nearest closing time today
        closes_min = min(r[2] for r in open_slots)
        closes_at = local_now.replace(hour=closes_min // 60, minute=closes_min % 60, second=0, microsecond=0)
        return {
            "status": "open",
            "closes_at": closes_at.isoformat(),
            "minutes_until_close": closes_min - current_minutes,
            "next_open_at": None,
            "minutes_until_next_open": 0,
            "today_times": today_times,
        }

    # 2. Check upcoming opening slots in next 7 days
    best_delta_minutes = float("inf")
    next_minutes = 0

    for delta_day in range(7):
        target_day = (current_weekday + delta_day) % 7
        day_offset = delta_day * 24 * 60

        for r in ranges:
            if r[0] != target_day:
                continue
            # If today, slot start must be in the future
            if delta_day == 0 and r[1] <= current_minutes:
                continue

            candidate_delta = (r[1] - current_minutes) if delta_day == 0 else (day_offset + r[1])
            if 0 <= candidate_delta < best_delta_minutes:
                best_delta_minutes = candidate_delta
                next_minutes = r[1]

    next_open_at = None
    status = "closed"

    if best_delta_minutes != float("inf"):
        next_dt = local_now + timedelta(minutes=best_delta_minutes)
        next_open_at = next_dt.replace(
            hour=next_minutes // 60,
            minute=next_minutes % 60,
            second=0,
            microsecond=0,
        ).isoformat()

        if best_delta_minutes <= OPENING_SOON_MINUTES:
            status = "opening_soon"

    return {
        "status": status,
        "closes_at": None,
        "minutes_until_close": None,
        "next_open_at": next_open_at,
        "minutes_until_next_open": int(best_delta_minutes) if best_delta_minutes != float("inf") else None,
        "today_times": today_times,
    }


def is_market_open_today(market: dict[str, Any], today_code: str) -> bool:
    """Check if market is scheduled to open today."""
    for rule in market.get("schedule", []):
        if not isinstance(rule, dict):
            continue
        if today_code in rule.get("days", []):
            return True
    return False


def format_market_payload(
    market: dict[str, Any],
    distance_km: float | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Format market dictionary with all computed fields for state attributes or service results."""
    open_info = get_market_open_status(market, now=now)
    location = market.get("location") or {}
    parking = market.get("parking") or {}
    amenities = market.get("amenities") or {}

    today_times_str = ""
    if open_info["today_times"]:
        today_times_str = ", ".join(
            f"{t['start']} - {t['end']}" for t in open_info["today_times"]
        )

    payload = {
        "id": market.get("id"),
        "name": market.get("name"),
        "address": market.get("address"),
        "district": market.get("district"),
        "state": market.get("state"),
        "status": open_info["status"],
        "operating_hours_today": today_times_str or None,
        "closes_at": open_info["closes_at"],
        "next_open_at": open_info["next_open_at"],
        "minutes_until_close": open_info["minutes_until_close"],
        "minutes_until_next_open": open_info["minutes_until_next_open"],
        "parking_available": parking.get("available", False),
        "parking_accessible": parking.get("accessible", False),
        "parking_notes": parking.get("notes") or None,
        "has_toilet": amenities.get("toilet", False),
        "has_prayer_room": amenities.get("prayer_room", False),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "gmaps_link": location.get("gmaps_link"),
        "schedule": market.get("schedule", []),
    }
    if distance_km is not None:
        payload["distance_km"] = distance_km

    return payload
