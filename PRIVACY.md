# Privacy & Data Policy

Your privacy is a core principle in the design of the **Cari Pasar Malam** Home Assistant integration. This document details how data and location information are handled.

---

## 1. Zero Outbound Location Transmission
* **Local-Only Location Processing**: Your Home Assistant coordinates (`zone.home`), household members' live GPS coordinates (`person.*`), and any custom coordinates supplied to actions or services **never leave your Home Assistant server**.
* **No Cloud Geolocation Queries**: The remote API ([pasarmalam.app](https://pasarmalam.app)) is queried **solely for catalog synchronization** (downloading the public directory of Malaysian night markets). The API request URL is simply `/api/v1/markets?limit=200&offset=...`. No latitude, longitude, entity names, or user identifiers are ever sent in query parameters, request headers, or body payloads.

## 2. Local Spatial Calculation
* All proximity math (calculating the Haversine great-circle distance between targets and markets), radius filtering (e.g., within 10 km), and status resolution (determining whether a market is open, opening soon, or closed) runs **100% locally in-memory** on your Home Assistant machine via Python.

## 3. Storage & Database Privacy
* **Local Cache**: The public market directory (~1,150 markets) is cached locally in Home Assistant's `.storage/caripasarmalam.cache` file to minimize network requests (updating at most once every 24 hours).
* **Recorder Protection**: Large sensor attributes containing market lists and distance countdowns are marked as `_unrecorded_attributes`. They are not committed to your Home Assistant SQLite/MariaDB database, preventing unwanted storage growth and eliminating persistent location history trails.

## 4. Third-Party Services & Links
* **Map Tiles**: The bundled Lovelace map card (`caripasarmalam-card`) displays OpenStreetMap tiles directly from your client browser with a `strict-origin-when-cross-origin` referrer policy. No Home Assistant authentication tokens or private URLs are sent to tile providers.
* **Turn-by-Turn Navigation**: When you tap "Navigate", the card launches your device's native navigation apps (Google Maps, Waze, or Apple Maps) using standard destination coordinates for the selected market. No personal location history is transmitted to any intermediary server.

## 5. Telemetry & Analytics
* This integration contains **no telemetry, no tracking scripts, and no usage analytics**.

---

If you have any questions or concerns regarding privacy, feel free to open a discussion or issue on our [GitHub repository](https://github.com/zubir2k/homeassistant-caripasarmalam).
