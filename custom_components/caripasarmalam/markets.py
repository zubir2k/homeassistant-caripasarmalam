"""Pure market logic: cleaning API records, distance, and open/closed status.

No Home Assistant imports, so it can be tested on its own.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MYT = ZoneInfo("Asia/Kuala_Lumpur")
DAY_INDEX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
DAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEK = 7 * 24 * 60
_POSTCODE = re.compile(r"^\s*\d{5}\s+")


def _minutes(hhmm: str) -> int | None:
    try:
        h, m = str(hhmm).strip().split(":")[:2]
        h, m = int(h), int(m)
    except (ValueError, AttributeError):
        return None
    if not (0 <= h <= 24 and 0 <= m < 60):
        return None
    return h * 60 + m


@dataclass
class Market:
    """One market, with its weekly sessions as minute ranges from Monday 00:00."""

    id: str
    name: str
    address: str
    district: str
    state: str
    lat: float
    lon: float
    gmaps: str | None
    parking: bool
    parking_accessible: bool
    toilet: bool
    prayer_room: bool
    schedule: list[dict]
    # (start, end) in minutes since Monday 00:00 MYT; end may exceed WEEK (Sun night -> Mon)
    sessions: list[tuple[int, int]] = field(default_factory=list)

    @classmethod
    def from_api(cls, raw: dict) -> "Market | None":
        loc = raw.get("location") or {}
        try:
            lat, lon = float(loc["latitude"]), float(loc["longitude"])
        except (KeyError, TypeError, ValueError):
            return None
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return None
        if str(raw.get("status", "Active")).lower() != "active":
            return None

        gmaps = loc.get("gmaps_link") or None
        if gmaps and "example" in gmaps:  # placeholder links in the seed data
            gmaps = None
        parking = raw.get("parking") or {}
        amen = raw.get("amenities") or {}
        schedule = raw.get("schedule") or []

        sessions: list[tuple[int, int]] = []
        for rule in schedule:
            for day in rule.get("days") or []:
                d = DAY_INDEX.get(str(day).lower()[:3])
                if d is None:
                    continue
                for t in rule.get("times") or []:
                    start, end = _minutes(t.get("start")), _minutes(t.get("end"))
                    if start is None or end is None or start == end:
                        continue
                    if end < start:  # runs past midnight, e.g. 17:00-01:00
                        end += 24 * 60
                    sessions.append((d * 1440 + start, d * 1440 + end))
        sessions.sort()

        return cls(
            id=str(raw.get("id")),
            name=str(raw.get("name") or raw.get("id")).strip(),
            address=str(raw.get("address") or "").strip(),
            district=_POSTCODE.sub("", str(raw.get("district") or "")).strip(),
            state=str(raw.get("state") or "").strip(),
            lat=lat,
            lon=lon,
            gmaps=gmaps,
            parking=bool(parking.get("available")),
            parking_accessible=bool(parking.get("accessible")),
            toilet=bool(amen.get("toilet")),
            prayer_room=bool(amen.get("prayer_room")),
            schedule=schedule,
            sessions=sessions,
        )

    def status_at(self, now: datetime, soon_minutes: int) -> dict:
        """Open/closed at `now` (any tz), with the closing or next opening time."""
        local = now.astimezone(MYT)
        week_start = (local - timedelta(days=local.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        m = local.weekday() * 1440 + local.hour * 60 + local.minute
        if not self.sessions:
            return {"status": "unknown"}

        # A session from last Sunday night can still be running early Monday: check the
        # sessions shifted one week back as well.
        for shift in (0, -WEEK):
            for start, end in self.sessions:
                if start + shift <= m < end + shift:
                    closes = week_start + timedelta(minutes=end + shift)
                    return {
                        "status": "open",
                        "closes_at": closes.isoformat(),
                        "minutes_left": int(end + shift - m),
                    }

        best = None
        for shift in (0, WEEK):
            for start, _end in self.sessions:
                s = start + shift
                if s > m and (best is None or s < best):
                    best = s
        if best is None:
            return {"status": "unknown"}
        opens = week_start + timedelta(minutes=best)
        wait = int(best - m)
        return {
            "status": "opening_soon" if wait <= soon_minutes else "closed",
            "opens_at": opens.isoformat(),
            "minutes_until": wait,
        }

    def hours_on(self, weekday: int) -> list[str]:
        """'HH:MM-HH:MM' for sessions starting on a weekday (0 = Monday)."""
        out = []
        for start, end in self.sessions:
            if start // 1440 == weekday:
                s, e = start % 1440, end % 1440
                out.append(f"{s // 60:02d}:{s % 60:02d}-{e // 60:02d}:{e % 60:02d}")
        return out

    def days(self) -> list[str]:
        return [DAY_CODES[d] for d in sorted({s // 1440 for s, _ in self.sessions})]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


RANK = {"open": 0, "opening_soon": 1, "closed": 2, "unknown": 3}


def nearby(
    markets: list[Market],
    lat: float,
    lon: float,
    radius_km: float,
    limit: int,
    now: datetime,
    soon_minutes: int,
) -> dict:
    """Everything a location sensor shows, computed from the cached dataset."""
    local = now.astimezone(MYT)
    found = []
    for mk in markets:
        dist = haversine_km(lat, lon, mk.lat, mk.lon)
        if dist <= radius_km:
            found.append((dist, mk))
    found.sort(key=lambda x: x[0])

    rows = []
    for dist, mk in found:
        st = mk.status_at(now, soon_minutes)
        rows.append(
            {
                "id": mk.id,
                "name": mk.name,
                "status": st["status"],
                "distance_km": round(dist, 2),
                "latitude": round(mk.lat, 6),
                "longitude": round(mk.lon, 6),
                "district": mk.district,
                "state": mk.state,
                "address": mk.address,
                "closes_at": st.get("closes_at"),
                "opens_at": st.get("opens_at"),
                "minutes_left": st.get("minutes_left"),
                "minutes_until": st.get("minutes_until"),
                "today": mk.hours_on(local.weekday()),
                "days": mk.days(),
                "parking": mk.parking,
                "toilet": mk.toilet,
                "prayer_room": mk.prayer_room,
                "gmaps": mk.gmaps,
            }
        )

    open_now = [r for r in rows if r["status"] == "open"]
    soon = [r for r in rows if r["status"] == "opening_soon"]
    upcoming = sorted(
        (r for r in rows if r.get("opens_at")), key=lambda r: (r["minutes_until"], r["distance_km"])
    )
    tonight = [r for r in rows if r["today"]]

    # Card list: open first, then opening soon, then the rest, nearest first within each
    shown = sorted(rows, key=lambda r: (RANK[r["status"]], r["distance_km"]))[:limit]

    featured = open_now[0] if open_now else (upcoming[0] if upcoming else None)
    return {
        "featured": featured,
        "total": len(rows),
        "open_count": len(open_now),
        "opening_soon_count": len(soon),
        "today_count": len(tonight),
        "nearest_open": open_now[0] if open_now else None,
        "next_opening": upcoming[0] if upcoming else None,
        "markets": shown,
    }
