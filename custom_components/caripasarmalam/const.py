"""Constants for the Cari Pasar Malam integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

DOMAIN = "caripasarmalam"
NAME = "Cari Pasar Malam"

# Public, keyless API (https://github.com/muazhazali/caripasarmalam). Read-only,
# 60 requests/minute per IP per route. limit is capped at 200 by the API.
API_BASE = "https://pasarmalam.app/api/v1"
API_MARKETS = f"{API_BASE}/markets"
API_PAGE_SIZE = 200
API_MAX_PAGES = 20  # safety stop: 4,000 markets
MARKET_URL = "https://pasarmalam.app/markets/{id}"

# The API sits behind Cloudflare: an identifying User-Agent is answered, a browser-like
# one gets 403 and a bare client a JS challenge. Always send this.
USER_AGENT = "homeassistant-caripasarmalam/{version} (+https://github.com/zubir2k/homeassistant-caripasarmalam)"

# The whole dataset is small (about 1,150 markets, 6 calls) so it is fetched in full
# and distance/open status is worked out locally for every tracked location.
DATASET_MAX_AGE_HOURS = 24
# How often the coordinator rescans zone.home and person entities
LOCATION_SCAN_MINUTES = 5

# Options
CONF_RADIUS = "radius"
CONF_MAX_MARKETS = "max_markets"
DEFAULT_RADIUS = 10  # km
MIN_RADIUS = 1
MAX_RADIUS = 50
DEFAULT_MAX_MARKETS = 20
MIN_MAX_MARKETS = 5
MAX_MAX_MARKETS = 50

# Same threshold as the pasarmalam.app map
OPENING_SOON_MINUTES = 120

STATUS_OPEN = "open"
STATUS_OPENING_SOON = "opening_soon"
STATUS_CLOSED = "closed"
STATUS_UNKNOWN = "unknown"  # no schedule in the dataset

HOME = "zone.home"


def get_device_info(entry_id: str) -> DeviceInfo:
    """Shared service device for all Cari Pasar Malam entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=NAME,
        manufacturer="CariPasarMalam (pasarmalam.app)",
        model="Market Directory",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://pasarmalam.app",
    )
