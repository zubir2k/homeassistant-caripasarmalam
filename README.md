![CariPasarMalam](/custom_components/caripasarmalam/brand/dark_logo.png)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that brings **[Cari Pasar Malam](https://pasarmalam.app)** night market directories and schedules directly into your smart home.

Find which pasar malam is open tonight near your home or wherever your family members are across Malaysia, complete with opening times, operating status, live distance, amenities, and calendar schedules.

---

## ✨ Features

* 🏠 **Home Zone Proximity**: Defaults to your `zone.home` location with a customizable radius (default 10 km).
* 👤 **Live Person Tracking**: Automatically discovers `person.*` entities with GPS coordinates and calculates the nearest pasar malam to wherever each person is right now (customizable radius, default 5 km).
* 🗺️ **Bundled Interactive Lovelace Map Card (`caripasarmalam-card`)**: Built-in Leaflet map card with target switcher pills (Home and family members), filter tags, and market popup details matching the web experience.
* ⚡ **Local In-Memory Spatial Matching**: Caches the entire Malaysian pasar malam directory (~1,139 markets) in Home Assistant's `.storage` once a day. All distance and schedule calculations run locally in Python without hammering the API.
* 📅 **Native Calendar Platform (`calendar`)**: Displays recurring weekly pasar malam schedules as native calendar events. Easily trigger automations 1 hour before the market opens!
* 🔔 **Sensors & Binary Sensors**:
  * `sensor.pasar_malam_<target>_nearest`: Nearest market open today, distance, status (`open`, `opening_soon`, `closed`), opening hours, parking, prayer room, toilet, and Google Maps directions link.
  * `sensor.pasar_malam_<target>_count`: Total number of pasar malam open today within radius.
  * `binary_sensor.pasar_malam_<target>_open_tonight`: `on` if any market is open today/tonight within radius.
* 🤖 **Action / Service (`caripasarmalam.get_nearby`)**:
  * Query markets on-demand around any person, zone, or GPS coordinates (`latitude`, `longitude`).
  * Returns structured response data for Automations, Voice Assist, and WhatsApp AI bots (**Pakbir AI**).
* 🇲🇾 **Pure Nationwide GPS**: Seamless tracking across all Malaysian states without manual state switching or boundary restrictions.
* 🌐 **Bilingual**: Full English and Bahasa Melayu support.

---

## 📦 Installation

### Option 1: Via HACS (Recommended)

1. Open **HACS** in your Home Assistant.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Add `https://github.com/zubir2k/homeassistant-caripasarmalam` with category **Integration**.
4. Click **Download**, then restart Home Assistant.

### Option 2: Manual Installation

1. Copy the `custom_components/caripasarmalam` folder into your Home Assistant's `config/custom_components/` directory.
2. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, go to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for **Cari Pasar Malam**.
3. Set your preferred options:
   * **Home Search Radius**: Default `10` km.
   * **Person Search Radius**: Default `5` km.
   * **Update Interval**: Default `30` minutes.

You can modify these options or filter tracked persons at any time by clicking **Configure** on the integration.

---

## 🗺️ Lovelace Map Card

A custom Lovelace card is bundled automatically with this integration.

Add it to any dashboard view:

```yaml
type: custom:caripasarmalam-card
entities:
  - sensor.pasarmalam_home
  - sensor.pasarmalam_zubir
map_height: 320       # px
list_limit: 6
show_closed: true
show_radius: true
tiles: auto           # auto, light, dark
language: auto        # auto, ms, en
# carto_key: xxxx     # optional, see below
```

- A tab per location; tap a market to fly to it on the map.
- Each row has **Map** (the market in Google Maps) and **Navigate**. The map popup has **Info** (the market's page on pasarmalam.app) and **Navigate**.
- **Navigate** opens the phone's own app chooser on Android (Google Maps, Waze, ...), a sheet with Apple Maps, Google Maps and Waze on iPhone/iPad, and Google Maps directions elsewhere.
- The button under the zoom controls re-centres on the selected person (or Home).
- Map tiles are OpenStreetMap; dark mode uses the same tiles colour-inverted. CARTO's Voyager and Dark Matter tiles now need a free key ([carto.com/basemaps/apikey](https://carto.com/basemaps/apikey)) or they show an "API KEY REQUIRED" watermark, so set `carto_key` if you prefer them.

---

## 🛠️ Action / Service Usage

### `caripasarmalam.get_nearby`

Find pasar malam near any target with structured response data:

```yaml
action: caripasarmalam.get_nearby
data:
  entity_id: person.zubir
  radius: 10
  day: today # 'today', 'tomorrow', 'all', 'wed', etc.
  limit: 5
response_variable: nearby_markets
```

Or query by raw GPS coordinates:

```yaml
action: caripasarmalam.get_nearby
data:
  latitude: 3.0125
  longitude: 101.7852
  radius: 8
  day: today
  limit: 3
response_variable: nearby_markets
```

Example response:

```json
{
  "count": 2,
  "requested_day": "today",
  "radius_km": 10.0,
  "nearest": {
    "name": "Pasar Malam Taman Jasmin",
    "distance_km": 3.2,
    "status": "open",
    "operating_hours_today": "16:00 - 23:00",
    "address": "Jalan Jasmin 3, Taman Jasmin, 43000 Kajang, Selangor",
    "has_toilet": false,
    "has_prayer_room": false,
    "parking_available": false,
    "gmaps_link": "https://www.google.com/maps/place/Pasar+Malam+Taman+Jasmin/..."
  },
  "markets": [...]
}
```

---

## 💡 Example Automations

### 1. Alert at 4:30 PM if there is a Pasar Malam near Home tonight

```yaml
alias: "Pasar Malam Petang Ini Alert"
trigger:
  - platform: time
    at: "16:30:00"
condition:
  - condition: state
    entity_id: binary_sensor.pasar_malam_home_open_tonight
    state: "on"
action:
  - action: notify.notify
    data:
      title: "Jom Pergi Pasar Malam! 🍢"
      message: >-
        {{ state_attr('sensor.pasar_malam_home_nearest', 'friendly_name') }}:
        {{ states('sensor.pasar_malam_home_nearest') }}
        ({{ state_attr('sensor.pasar_malam_home_nearest', 'distance_km') }} km away)
        buka hari ini dari {{ state_attr('sensor.pasar_malam_home_nearest', 'operating_hours_today') }}.
```

### 2. Notify when nearing an open Pasar Malam on Friday evening

```yaml
alias: "Pasar Malam Near Me on Friday"
trigger:
  - platform: time_pattern
    minutes: "/30"
condition:
  - condition: time
    weekday:
      - fri
  - condition: numeric_state
    entity_id: sensor.pasar_malam_zubir_markets_today_count
    above: 0
action:
  - action: notify.mobile_app_zubir_phone
    data:
      title: "Pasar Malam Berdekatan Anda"
      message: >-
        Pasar malam terdekat dengan lokasi anda ialah {{ states('sensor.pasar_malam_zubir_nearest') }}
        ({{ state_attr('sensor.pasar_malam_zubir_nearest', 'distance_km') }} km).
```

---

## 📜 Credits & License

* Data source: **[CariPasarMalam](https://pasarmalam.app)** by [@muazhazali](https://github.com/muazhazali/caripasarmalam).
* Licensed under the [MIT License](LICENSE).
