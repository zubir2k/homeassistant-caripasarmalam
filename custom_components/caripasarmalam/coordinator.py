"""DataUpdateCoordinator for CariPasarMalam."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_MARKETS_URL,
    API_PAGE_LIMIT,
    CACHE_TTL_HOURS,
    CONF_HOME_RADIUS,
    CONF_PERSON_RADIUS,
    CONF_TRACKED_PERSONS,
    DEFAULT_HOME_RADIUS,
    DEFAULT_PERSON_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MYT,
    STORAGE_KEY,
    STORAGE_VERSION,
    VERSION,
    WEEKDAY_CODES,
)
from .helpers import (
    format_market_payload,
    get_market_open_status,
    haversine_distance,
    is_market_open_today,
)

_LOGGER = logging.getLogger(__name__)

type CariPasarMalamConfigEntry = ConfigEntry["CariPasarMalamCoordinator"]


class CariPasarMalamCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch pasar malam data and track nearest markets."""

    config_entry: CariPasarMalamConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Cari Pasar Malam",
            update_interval=timedelta(minutes=scan_interval),
        )
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.markets: list[dict[str, Any]] = []
        self.last_catalog_update: datetime | None = None
        self._loaded_from_storage = False

    async def _async_load_cache(self) -> None:
        """Load cached markets from disk storage."""
        if self._loaded_from_storage:
            return
        data = await self._store.async_load()
        if data and isinstance(data, dict):
            stored_markets = data.get("markets", [])
            stored_ts = data.get("last_fetched")
            if stored_markets and isinstance(stored_markets, list):
                self.markets = stored_markets
                if stored_ts:
                    try:
                        self.last_catalog_update = datetime.fromisoformat(stored_ts)
                    except ValueError:
                        self.last_catalog_update = None
                _LOGGER.debug(
                    "Loaded %d markets from storage (fetched at %s)",
                    len(self.markets),
                    stored_ts,
                )
        self._loaded_from_storage = True

    async def _async_save_cache(self) -> None:
        """Save current markets catalog to storage."""
        await self._store.async_save({
            "markets": self.markets,
            "last_fetched": self.last_catalog_update.isoformat() if self.last_catalog_update else None,
        })

    async def async_fetch_all_markets(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        """Fetch all markets from the pasarmalam.app API with pagination."""
        headers = {
            "User-Agent": f"HomeAssistant-CariPasarMalam/{VERSION} (+https://github.com/zubir2k/homeassistant-caripasarmalam)",
            "Accept": "application/json",
        }

        all_markets: list[dict[str, Any]] = []
        offset = 0

        while True:
            params: dict[str, Any] = {
                "limit": API_PAGE_LIMIT,
                "offset": offset,
                "status": "Active",
            }

            try:
                async with session.get(
                    API_MARKETS_URL,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status == 429:
                        _LOGGER.warning("Rate limited by pasarmalam.app API. Using cached dataset.")
                        break
                    if resp.status != 200:
                        _LOGGER.error("API error %s when fetching markets offset %d", resp.status, offset)
                        break

                    payload = await resp.json()
                    data = payload.get("data", [])
                    if not data or not isinstance(data, list):
                        break

                    all_markets.extend(data)
                    meta = payload.get("meta", {})
                    count = meta.get("count", len(data))

                    if count < API_PAGE_LIMIT or len(data) < API_PAGE_LIMIT:
                        break

                    offset += len(data)
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.warning("Network error fetching markets catalog: %s", err)
                break

        return all_markets

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh pasar malam data and calculate proximity for all tracked locations."""
        session = async_get_clientsession(self.hass)
        await self._async_load_cache()

        now_myt = datetime.now(MYT)
        cache_expired = (
            self.last_catalog_update is None
            or (now_myt - self.last_catalog_update) > timedelta(hours=CACHE_TTL_HOURS)
            or not self.markets
        )

        if cache_expired:
            _LOGGER.debug("Market catalog cache expired or empty. Refreshing from pasarmalam.app...")
            fresh_markets = await self.async_fetch_all_markets(session)
            if fresh_markets:
                self.markets = fresh_markets
                self.last_catalog_update = now_myt
                await self._async_save_cache()
            elif not self.markets:
                raise UpdateFailed("Failed to fetch markets catalog and no local cache available.")

        # Evaluate targets
        today_code = WEEKDAY_CODES.get(now_myt.weekday(), "mon")
        home_radius = float(
            self.config_entry.options.get(
                CONF_HOME_RADIUS,
                self.config_entry.data.get(CONF_HOME_RADIUS, DEFAULT_HOME_RADIUS),
            )
        )
        person_radius = float(
            self.config_entry.options.get(
                CONF_PERSON_RADIUS,
                self.config_entry.data.get(CONF_PERSON_RADIUS, DEFAULT_PERSON_RADIUS),
            )
        )
        tracked_persons = self.config_entry.options.get(
            CONF_TRACKED_PERSONS,
            self.config_entry.data.get(CONF_TRACKED_PERSONS, []),
        )

        locations_result: dict[str, Any] = {}

        # 1. Process zone.home
        home_state = self.hass.states.get("zone.home")
        home_lat = (
            float(home_state.attributes[ATTR_LATITUDE])
            if home_state and ATTR_LATITUDE in home_state.attributes
            else self.hass.config.latitude
        )
        home_lon = (
            float(home_state.attributes[ATTR_LONGITUDE])
            if home_state and ATTR_LONGITUDE in home_state.attributes
            else self.hass.config.longitude
        )

        locations_result["zone.home"] = self._compute_location_summary(
            lat=home_lat,
            lon=home_lon,
            radius_km=home_radius,
            now=now_myt,
            today_code=today_code,
            name="Home",
        )

        # 2. Process person.* entities
        all_persons = self.hass.states.async_entity_ids("person")
        for person_id in all_persons:
            # If user explicitly configured tracked persons and this person isn't in it, skip
            if tracked_persons and person_id not in tracked_persons:
                continue

            person_state = self.hass.states.get(person_id)
            if not person_state:
                continue

            lat = person_state.attributes.get(ATTR_LATITUDE)
            lon = person_state.attributes.get(ATTR_LONGITUDE)
            friendly_name = person_state.attributes.get("friendly_name", person_id.split(".")[-1])

            if lat is not None and lon is not None:
                locations_result[person_id] = self._compute_location_summary(
                    lat=float(lat),
                    lon=float(lon),
                    radius_km=person_radius,
                    now=now_myt,
                    today_code=today_code,
                    name=friendly_name,
                )
            else:
                locations_result[person_id] = {
                    "has_coordinates": False,
                    "name": friendly_name,
                    "nearest_market_today": None,
                    "open_today_count": 0,
                    "open_now_count": 0,
                    "open_tonight": False,
                    "markets_today": [],
                    "all_nearby_markets": [],
                }

        return {
            "catalog_count": len(self.markets),
            "last_catalog_update": self.last_catalog_update.isoformat() if self.last_catalog_update else None,
            "today_code": today_code,
            "locations": locations_result,
        }

    def _compute_location_summary(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        now: datetime,
        today_code: str,
        name: str,
    ) -> dict[str, Any]:
        """Compute distances and open status for all markets relative to a coordinate point."""
        nearby_all: list[dict[str, Any]] = []
        nearby_today: list[dict[str, Any]] = []

        for market in self.markets:
            loc = market.get("location")
            if not loc or "latitude" not in loc or "longitude" not in loc:
                continue

            m_lat = float(loc["latitude"])
            m_lon = float(loc["longitude"])
            dist = haversine_distance(lat, lon, m_lat, m_lon)

            if dist <= radius_km:
                payload = format_market_payload(market, distance_km=dist, now=now)
                nearby_all.append(payload)

                if is_market_open_today(market, today_code):
                    nearby_today.append(payload)

        # Sort both by distance ascending
        nearby_all.sort(key=lambda m: m.get("distance_km", 9999))
        nearby_today.sort(key=lambda m: m.get("distance_km", 9999))

        nearest_today = nearby_today[0] if nearby_today else None
        open_now_count = sum(1 for m in nearby_today if m.get("status") == "open")

        return {
            "has_coordinates": True,
            "latitude": lat,
            "longitude": lon,
            "name": name,
            "radius_km": radius_km,
            "nearest_market_today": nearest_today,
            "open_today_count": len(nearby_today),
            "open_now_count": open_now_count,
            "open_tonight": len(nearby_today) > 0,
            "markets_today": nearby_today,
            "all_nearby_markets": nearby_all,
        }

    def find_nearby_markets(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        day_filter: str = "today",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Synchronously rank markets around any coordinate point (used by services/actions)."""
        now_myt = datetime.now(MYT)
        today_code = WEEKDAY_CODES.get(now_myt.weekday(), "mon")
        tomorrow_code = WEEKDAY_CODES.get((now_myt.weekday() + 1) % 7, "tue")

        day_req = day_filter.lower().strip()
        if day_req == "today":
            target_day: str | None = today_code
        elif day_req == "tomorrow":
            target_day = tomorrow_code
        elif day_req in ("all", "any"):
            target_day = None
        elif day_req in WEEKDAY_CODES.values():
            target_day = day_req
        else:
            target_day = today_code

        results: list[dict[str, Any]] = []

        for market in self.markets:
            loc = market.get("location")
            if not loc or "latitude" not in loc or "longitude" not in loc:
                continue

            m_lat = float(loc["latitude"])
            m_lon = float(loc["longitude"])
            dist = haversine_distance(lat, lon, m_lat, m_lon)

            if dist <= radius_km:
                if target_day is not None and not is_market_open_today(market, target_day):
                    continue

                payload = format_market_payload(market, distance_km=dist, now=now_myt)
                results.append(payload)

        results.sort(key=lambda m: m.get("distance_km", 9999))
        return results[:limit]
