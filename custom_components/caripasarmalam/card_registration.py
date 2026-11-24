"""Serve and register the bundled CariPasarMalam Lovelace card."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "caripasarmalam-card.js"
CARD_URL_BASE = f"/{DOMAIN}_static"
CARD_URL = f"{CARD_URL_BASE}/{CARD_FILENAME}"

_URL_KEY = f"{DOMAIN}_card_url"
_INJECTED_KEY = f"{DOMAIN}_card_injected"
_REGISTERED_KEY = f"{DOMAIN}_card_registered"
_LOCK_KEY = f"{DOMAIN}_card_lock"
_LOVELACE_KEY = "lovelace"


def _lovelace_resources(hass: HomeAssistant) -> tuple[str | None, Any]:
    """Return (resource_mode, resource_collection), or (None, None) if unavailable."""
    data = hass.data.get(_LOVELACE_KEY)
    if data is None:
        return None, None
    if isinstance(data, dict):
        return data.get("mode"), data.get("resources")
    mode = getattr(data, "resource_mode", None)
    if mode is None:
        mode = getattr(data, "mode", None)
    return mode, getattr(data, "resources", None)


async def _async_ensure_loaded(resources: Any) -> bool:
    """Make sure the resource store has been read from disk."""
    if getattr(resources, "loaded", True):
        return True
    try:
        await resources.async_get_info()
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not load Lovelace resources", exc_info=True)
    return bool(getattr(resources, "loaded", False))


def _our_resources(resources: Any) -> list[dict[str, Any]]:
    return [
        item
        for item in (resources.async_items() or [])
        if str(item.get("url", "")).split("?", 1)[0] == CARD_URL
    ]


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and make dashboards load it."""
    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    is_file = await hass.async_add_executor_job(card_path.is_file)
    if not is_file:
        _LOGGER.warning("CariPasarMalam card not found at %s", card_path)
        return

    lock = hass.data.setdefault(_LOCK_KEY, asyncio.Lock())
    async with lock:
        url = hass.data.get(_URL_KEY)
        if url is None:
            await _async_register_static_path(hass, card_path.parent)
            integration = await async_get_integration(hass, DOMAIN)
            digest = await hass.async_add_executor_job(_file_digest, card_path)
            url = f"{CARD_URL}?v={integration.version or '0'}-{digest}"
            hass.data[_URL_KEY] = url

        mode, resources = _lovelace_resources(hass)
        if mode == "storage" and resources is not None:
            try:
                if await _async_ensure_loaded(resources):
                    await _async_sync_resource(resources, url)
                    _LOGGER.debug("CariPasarMalam card registered as Lovelace resource %s", url)
                    hass.data[_REGISTERED_KEY] = True
                    return
                _LOGGER.debug("Lovelace resources not loaded; injecting the card script instead")
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Could not register the CariPasarMalam card as a Lovelace resource; "
                    "injecting the card script instead",
                    exc_info=True,
                )

        if not hass.data.get(_INJECTED_KEY):
            hass.data[_INJECTED_KEY] = True
            add_extra_js_url(hass, url)
            _LOGGER.debug("CariPasarMalam card injected via add_extra_js_url: %s", url)
        hass.data[_REGISTERED_KEY] = True


async def async_unregister_card(hass: HomeAssistant) -> None:
    """Remove our Lovelace resource."""
    hass.data.pop(_REGISTERED_KEY, None)
    mode, resources = _lovelace_resources(hass)
    if mode != "storage" or resources is None:
        return
    try:
        if not await _async_ensure_loaded(resources):
            return
        for item in _our_resources(resources):
            await resources.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not remove the CariPasarMalam Lovelace resource", exc_info=True)


async def _async_register_static_path(hass: HomeAssistant, folder: Path) -> None:
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_BASE, str(folder), cache_headers=False)]
        )
    except ImportError:
        hass.http.register_static_path(CARD_URL_BASE, str(folder), cache_headers=False)
    except RuntimeError:
        _LOGGER.debug("CariPasarMalam static path already registered")


async def _async_sync_resource(resources: Any, url: str) -> None:
    """Create our resource or update it."""
    existing = _our_resources(resources)

    if not existing:
        await resources.async_create_item({"res_type": "module", "url": url})
        return

    keep, duplicates = existing[0], existing[1:]
    if keep.get("url") != url or keep.get("type") != "module":
        await resources.async_update_item(keep["id"], {"res_type": "module", "url": url})
    for extra in duplicates:
        await resources.async_delete_item(extra["id"])
