"""Constants for the CariPasarMalam integration."""
from __future__ import annotations

from zoneinfo import ZoneInfo

DOMAIN = "caripasarmalam"
VERSION = "0.1.0"

# Timezone
MYT = ZoneInfo("Asia/Kuala_Lumpur")

# Configuration keys
CONF_HOME_RADIUS = "home_radius"
CONF_PERSON_RADIUS = "person_radius"
CONF_TRACKED_PERSONS = "tracked_persons"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_HOME_RADIUS = 10  # km
DEFAULT_PERSON_RADIUS = 5  # km
DEFAULT_SCAN_INTERVAL = 30  # minutes

MIN_RADIUS = 1
MAX_RADIUS = 50

# API Endpoints
API_BASE_URL = "https://pasarmalam.app/api/v1"
API_MARKETS_URL = f"{API_BASE_URL}/markets"
API_PAGE_LIMIT = 200

# Cache configuration
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.cache"
CACHE_TTL_HOURS = 24

# Market status thresholds
OPENING_SOON_MINUTES = 120

# Day mapping (Python weekday: 0=Mon, 6=Sun)
WEEKDAY_CODES = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}

WEEKDAY_NAMES_EN = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}

WEEKDAY_NAMES_MS = {
    "mon": "Isnin",
    "tue": "Selasa",
    "wed": "Rabu",
    "thu": "Khamis",
    "fri": "Jumaat",
    "sat": "Sabtu",
    "sun": "Ahad",
}
