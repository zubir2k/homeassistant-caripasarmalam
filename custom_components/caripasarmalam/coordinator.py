"""Coordinator: keeps the market dataset fresh and knows which locations to track.

The dataset is fetched whole (about 1,150 markets) at most once a day and kept
in .storage, so a restart does not refetch it. Every few minutes the coordinator rescans
zone.home and every person entity with GPS; the sensors then work out distance and
open/closed status locally, every minute, from the live coordinates.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from caripasarmalam import CariPasarMalamClient, CariPasarMalamError, Market

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration

from .const import (
    DATASET_MAX_AGE_HOURS,
    DOMAIN,
    HOME,
    LOCATION_SCAN_MINUTES,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.cache"

type CariPasarMalamConfigEntry = ConfigEntry["CariPasarMalamCoordinator"]


def cache_store(hass: HomeAssistant) -> Store:
    """Dataset kept in .storage so a restart or reload does not refetch it."""
    return Store(hass, STORAGE_VERSION, STORAGE_KEY)


class CariPasarMalamCoordinator(DataUpdateCoordinator[dict]):
    """Dataset + the list of locations (zone.home and people with GPS)."""

    config_entry: CariPasarMalamConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CariPasarMalamConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Cari Pasar Malam",
            update_interval=timedelta(minutes=LOCATION_SCAN_MINUTES),
        )
        self.markets: list[Market] = []
        self.fetched: datetime | None = None
        self.raw_count = 0
        self.last_error: str | None = None
        self._store = cache_store(hass)
        self._loaded = False
        self._user_agent: str | None = None

    async def _ua(self) -> str:
        if self._user_agent is None:
            integration = await async_get_integration(self.hass, DOMAIN)
            self._user_agent = USER_AGENT.format(version=integration.version or "0")
        return self._user_agent

    def _parse(self, raw: list[dict]) -> list[Market]:
        return [m for m in (Market.from_api(r) for r in raw) if m is not None]

    async def _async_load_cache(self) -> None:
        self._loaded = True
        try:
            stored = await self._store.async_load() or {}
            raw = stored.get("markets") or []
            if raw:
                self.markets = await self.hass.async_add_executor_job(self._parse, raw)
                self.raw_count = len(raw)
                self.fetched = datetime.fromisoformat(stored["fetched"])
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Ignoring unreadable Cari Pasar Malam cache: %s", err)
            self.markets, self.fetched = [], None

    def _stale(self) -> bool:
        if not self.markets or self.fetched is None:
            return True
        return datetime.now(timezone.utc) - self.fetched > timedelta(hours=DATASET_MAX_AGE_HOURS)

    async def _async_refresh_dataset(self) -> None:
        session = async_get_clientsession(self.hass)
        client = CariPasarMalamClient(session=session, user_agent=await self._ua())
        try:
            raw = await client.fetch_raw_markets()
        except (CariPasarMalamError, aiohttp.ClientError, TimeoutError, ValueError) as err:
            self.last_error = str(err)
            if self.markets:
                _LOGGER.debug("Dataset refresh failed (%s); keeping the cached copy", err)
                return
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_fetch",
                translation_placeholders={"error": str(err)},
            ) from err
        if not raw:
            self.last_error = "empty response"
            if not self.markets:
                raise UpdateFailed(translation_domain=DOMAIN, translation_key="empty_dataset")
            return
        self.markets = await self.hass.async_add_executor_job(self._parse, raw)
        self.raw_count = len(raw)
        self.fetched = datetime.now(timezone.utc)
        self.last_error = None
        await self._store.async_save({"fetched": self.fetched.isoformat(), "markets": raw})
        _LOGGER.debug("Fetched %s markets (%s usable)", len(raw), len(self.markets))

    def locations(self) -> dict[str, dict[str, Any]]:
        """zone.home and every person with GPS, with their live coordinates."""
        found: dict[str, dict[str, Any]] = {}
        home = self.hass.states.get(HOME)
        if home and home.attributes.get("latitude") is not None:
            found[HOME] = {
                "latitude": home.attributes["latitude"],
                "longitude": home.attributes["longitude"],
                "name": home.attributes.get("friendly_name", "Home"),
            }
        for entity_id in self.hass.states.async_entity_ids("person"):
            st = self.hass.states.get(entity_id)
            if st is None:
                continue
            lat, lon = st.attributes.get("latitude"), st.attributes.get("longitude")
            if lat is None or lon is None:
                continue
            found[entity_id] = {
                "latitude": lat,
                "longitude": lon,
                "name": st.attributes.get("friendly_name", entity_id.split(".", 1)[1]),
            }
        return found

    async def _async_update_data(self) -> dict:
        if not self._loaded:
            await self._async_load_cache()
        if self._stale():
            await self._async_refresh_dataset()
        return {"locations": self.locations(), "market_count": len(self.markets)}
