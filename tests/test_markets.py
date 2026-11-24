"""Pure schedule / distance logic."""
from datetime import datetime

from custom_components.caripasarmalam.markets import MYT, Market, haversine_km, nearby


def _m(schedule):
    return Market.from_api(
        {"id": "x", "name": "X", "status": "Active", "schedule": schedule,
         "location": {"latitude": 3.0, "longitude": 101.8, "gmaps_link": ""}}
    )


def test_open_and_closing():
    mk = _m([{"days": ["tue"], "times": [{"start": "17:00", "end": "23:00"}]}])
    st = mk.status_at(datetime(2026, 11, 24, 20, 0, tzinfo=MYT), 120)  # Tuesday
    assert st["status"] == "open" and st["minutes_left"] == 180


def test_past_midnight_still_open():
    mk = _m([{"days": ["tue"], "times": [{"start": "17:00", "end": "01:00"}]}])
    st = mk.status_at(datetime(2026, 11, 25, 0, 30, tzinfo=MYT), 120)  # Wed 00:30
    assert st["status"] == "open" and st["minutes_left"] == 30


def test_sunday_night_into_monday():
    mk = _m([{"days": ["sun"], "times": [{"start": "18:00", "end": "01:00"}]}])
    st = mk.status_at(datetime(2026, 11, 30, 0, 15, tzinfo=MYT), 120)  # Mon 00:15
    assert st["status"] == "open"


def test_opening_soon_and_next_week():
    mk = _m([{"days": ["tue"], "times": [{"start": "17:00", "end": "23:00"}]}])
    assert mk.status_at(datetime(2026, 11, 24, 15, 30, tzinfo=MYT), 120)["status"] == "opening_soon"
    later = mk.status_at(datetime(2026, 11, 24, 23, 30, tzinfo=MYT), 120)
    assert later["status"] == "closed" and later["minutes_until"] == 7 * 1440 - 390


def test_no_schedule_is_unknown():
    assert _m([]).status_at(datetime(2026, 11, 24, 20, 0, tzinfo=MYT), 120)["status"] == "unknown"


def test_postcode_stripped_and_placeholder_link():
    mk = Market.from_api({"id": "a", "name": "A", "district": "43950 Sungai Pelek", "schedule": [],
                          "location": {"latitude": 2.66, "longitude": 101.68,
                                       "gmaps_link": "https://maps.app.goo.gl/example2"}})
    assert mk.district == "Sungai Pelek" and mk.gmaps is None


def test_nearby_orders_open_first(markets_payload):
    mks = [Market.from_api(r) for r in markets_payload["data"]]
    res = nearby(mks, 2.9930, 101.7890, 10, 20, datetime(2026, 11, 24, 20, 0, tzinfo=MYT), 120)
    statuses = [m["status"] for m in res["markets"]]
    assert statuses == sorted(statuses, key=lambda s: {"open": 0, "opening_soon": 1, "closed": 2, "unknown": 3}[s])
    assert round(haversine_km(3.0, 101.0, 3.0, 101.01), 2) == 1.11
