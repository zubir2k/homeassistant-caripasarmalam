/**
 * CariPasarMalam Card for Home Assistant
 *
 * Interactive Leaflet Map card showing nearby night markets (pasar malam)
 * around Home and tracked persons with live status, distances, hours, and navigation.
 *
 * Modeled after pasarmalam.app/map and homeassistant-jejakmasjid.
 * MIT License
 */

const CARD_VERSION = "0.2.0";
const BASE = new URL(".", import.meta.url).pathname.replace(/\/$/, "");
const VERSION = new URL(import.meta.url).searchParams.get("v") || CARD_VERSION;

const T = {
  en: {
    title: "Cari Pasar Malam",
    home: "Home",
    all: "All Markets",
    today: "Open Today",
    openNow: "Open Now",
    openingSoon: "Opening Soon",
    closed: "Closed",
    opensIn: "Opens in",
    closesIn: "Closes in",
    fromHere: "from here",
    getDirections: "Get Directions",
    viewDetails: "View Details",
    parking: "Parking",
    toilet: "Toilet",
    prayerRoom: "Surau",
    currentLocation: "Current location",
    noSensor: "No CariPasarMalam sensors found in Home Assistant.",
    noMarkets: "No markets found within search radius.",
    todayTag: "Today",
    daysFull: {
      mon: "Monday",
      tue: "Tuesday",
      wed: "Wednesday",
      thu: "Thursday",
      fri: "Friday",
      sat: "Saturday",
      sun: "Sunday",
    },
  },
  ms: {
    title: "Cari Pasar Malam",
    home: "Rumah",
    all: "Semua",
    today: "Buka Hari Ini",
    openNow: "Buka Sekarang",
    openingSoon: "Akan Buka",
    closed: "Tutup",
    opensIn: "Akan buka dalam",
    closesIn: "Akan tutup dalam",
    fromHere: "dari sini",
    getDirections: "Pandu Arah",
    viewDetails: "Maklumat Lanjut",
    parking: "Parkir",
    toilet: "Tandas",
    prayerRoom: "Surau",
    currentLocation: "Lokasi semasa",
    noSensor: "Tiada sensor CariPasarMalam ditemui dalam Home Assistant.",
    noMarkets: "Tiada pasar malam dijumpai dalam lingkungan.",
    todayTag: "Hari Ini",
    daysFull: {
      mon: "Isnin",
      tue: "Selasa",
      wed: "Rabu",
      thu: "Khamis",
      fri: "Jumaat",
      sat: "Sabtu",
      sun: "Ahad",
    },
  },
};

const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c]
  );

const navUrl = (lat, lon, name) => {
  const isAndroid = /Android/i.test(navigator.userAgent || "");
  const isIos =
    /iPhone|iPad|iPod/i.test(navigator.userAgent || "") ||
    (/Macintosh/.test(navigator.userAgent || "") && navigator.maxTouchPoints > 1);

  if (isAndroid) {
    return `geo:${lat},${lon}?q=${lat},${lon}(${encodeURIComponent(name)})`;
  }
  if (isIos) {
    return `maps://?daddr=${lat},${lon}&dirflg=d`;
  }
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}&travelmode=driving`;
};

let leafletPromise;
function loadLeaflet() {
  if (window.L && window.L.map) return Promise.resolve(window.L);
  if (!leafletPromise) {
    leafletPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = `${BASE}/leaflet.js?v=1.9.4`;
      s.onload = () => resolve(window.L);
      s.onerror = () => reject(new Error("Leaflet failed to load"));
      document.head.appendChild(s);
    });
  }
  return leafletPromise;
}

class CariPasarMalamCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selectedTarget = null;
    this._filter = "today"; // "today" | "all" | "open"
    this._map = null;
    this._markersLayer = null;
    this._userInteracted = false;
  }

  setConfig(config) {
    this._config = {
      title: config.title || "Cari Pasar Malam",
      map_height: config.map_height || 420,
      filter: config.filter || "today",
      language: config.language || "auto",
      ...config,
    };
    if (["today", "all", "open"].includes(this._config.filter)) {
      this._filter = this._config.filter;
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 6;
  }

  _getLang() {
    if (this._config.language === "ms" || this._config.language === "en") {
      return this._config.language;
    }
    const haLang = this._hass?.language || navigator.language || "en";
    return haLang.startsWith("ms") || haLang.startsWith("my") ? "ms" : "en";
  }

  _getTargetEntities() {
    if (!this._hass) return [];
    const sensors = [];
    for (const [entityId, stateObj] of Object.entries(this._hass.states)) {
      if (
        entityId.startsWith("sensor.") &&
        entityId.endsWith("_nearest_market") &&
        stateObj.attributes &&
        stateObj.attributes.target
      ) {
        sensors.push(stateObj);
      }
    }
    sensors.sort((a, b) => {
      if (a.attributes.target === "zone.home") return -1;
      if (b.attributes.target === "zone.home") return 1;
      return (a.attributes.target_name || "").localeCompare(b.attributes.target_name || "");
    });
    return sensors;
  }

  _formatCountdown(minutes, isClosing, t) {
    if (typeof minutes !== "number" || minutes <= 0) return "";
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    const timeStr = h > 0 ? (m > 0 ? `${h}h ${m}m` : `${h}h`) : `${m}m`;
    const prefix = isClosing ? t.closesIn : t.opensIn;
    return `${prefix} ${timeStr}`;
  }

  _formatScheduleDays(schedule, lang, t) {
    if (!Array.isArray(schedule) || schedule.length === 0) return "";
    const parts = [];
    const daysDict = t.daysFull;
    for (const rule of schedule) {
      if (!rule || !Array.isArray(rule.days)) continue;
      const dayNames = rule.days.map((d) => daysDict[d] || d);
      const times = rule.times || [];
      const timeStr = times.map((tm) => `${tm.start || ""}-${tm.end || ""}`).join(", ");
      parts.push(`${dayNames.join(", ")} ${timeStr}`);
    }
    return parts.join("; ");
  }

  _render() {
    if (!this._hass || !this.shadowRoot) return;

    const lang = this._getLang();
    const t = T[lang] || T.en;
    const targets = this._getTargetEntities();

    if (!targets.length) {
      this.shadowRoot.innerHTML = `
        <ha-card style="padding: 24px; text-align: center; color: var(--secondary-text-color);">
          <ha-icon icon="mdi:store-off" style="--mdc-icon-size: 40px; margin-bottom: 8px;"></ha-icon>
          <div>${t.noSensor}</div>
        </ha-card>
      `;
      return;
    }

    if (!this._selectedTarget || !targets.some((s) => s.attributes.target === this._selectedTarget)) {
      this._selectedTarget = targets[0].attributes.target;
    }

    const currentSensor = targets.find((s) => s.attributes.target === this._selectedTarget) || targets[0];
    const attrs = currentSensor.attributes || {};
    const radiusKm = attrs.radius_km || 10;
    const allNearby = attrs.all_nearby_markets || [];
    const marketsToday = attrs.markets_today || [];
    const openTodayCount = attrs.open_today_count || 0;
    const openNowCount = attrs.open_now_count || 0;

    // Filter displayed markets
    let displayedMarkets = allNearby;
    if (this._filter === "today") {
      displayedMarkets = marketsToday;
    } else if (this._filter === "open") {
      displayedMarkets = marketsToday.filter((m) => m.status === "open");
    }

    // Origin coordinates
    const originLat = attrs.target_latitude;
    const originLon = attrs.target_longitude;

    // Render skeleton if not built
    if (!this.shadowRoot.getElementById("map")) {
      this.shadowRoot.innerHTML = `
        <link rel="stylesheet" href="${BASE}/leaflet.css?v=1.9.4">
        <style>
          :host {
            --cpm-teal: #00a29a;
            --cpm-teal-dark: #007a74;
            --cpm-amber: #f59e0b;
            --cpm-blue: #2563eb;
            display: block;
          }
          ha-card {
            overflow: hidden;
            background: var(--card-background-color, #ffffff);
            border-radius: var(--ha-card-border-radius, 16px);
            font-family: var(--paper-font-body1_-_font-family, inherit);
            box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0, 0, 0, 0.08));
          }
          .cpm-header {
            padding: 14px 16px 12px;
            background: var(--primary-background-color, #ffffff);
            border-bottom: 1px solid var(--divider-color, #e2e8f0);
          }
          .cpm-title-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
          }
          .cpm-title {
            font-size: 1.15rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--primary-text-color, #0f172a);
          }
          .cpm-pills {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
          }
          .cpm-pill {
            padding: 5px 12px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            background: var(--secondary-background-color, #f1f5f9);
            color: var(--secondary-text-color, #64748b);
            border: 1px solid var(--divider-color, #cbd5e1);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 4px;
          }
          .cpm-pill.active {
            background: #0f172a;
            color: #ffffff;
            border-color: #0f172a;
          }
          .cpm-filter-bar {
            display: flex;
            gap: 8px;
            padding: 10px 16px;
            background: var(--card-background-color, #ffffff);
            border-bottom: 1px solid var(--divider-color, #e2e8f0);
            overflow-x: auto;
          }
          .cpm-filter-btn {
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            background: none;
            border: 1px solid var(--divider-color, #e2e8f0);
            color: var(--secondary-text-color, #64748b);
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s ease;
          }
          .cpm-filter-btn.active {
            background: var(--cpm-teal);
            color: #ffffff;
            border-color: var(--cpm-teal);
          }
          #map {
            width: 100%;
            height: ${Number(this._config.map_height)}px;
            position: relative;
            z-index: 0;
            background: #e2e8f0;
          }
          .leaflet-container {
            font-family: inherit;
          }
          /* Card style popup matching pasarmalam.app */
          .leaflet-popup-content-wrapper {
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            padding: 0;
            overflow: hidden;
            border: 1px solid rgba(0, 0, 0, 0.06);
          }
          .leaflet-popup-content {
            margin: 0;
            line-height: 1.45;
          }
          .cpm-popup {
            padding: 18px 20px 16px;
            min-width: 270px;
            max-width: 340px;
            font-family: var(--paper-font-body1_-_font-family, inherit);
          }
          .cpm-pop-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 6px;
          }
          .cpm-pop-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.25;
            letter-spacing: -0.01em;
          }
          .cpm-status-pill {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 9999px;
            white-space: nowrap;
          }
          .cpm-status-open {
            background: #dcfce7;
            color: #15803d;
          }
          .cpm-status-soon {
            background: #fef3c7;
            color: #b45309;
          }
          .cpm-status-closed {
            background: #e2e8f0;
            color: #475569;
          }
          .cpm-pop-sub {
            font-size: 0.88rem;
            color: #475569;
            margin-bottom: 6px;
          }
          .cpm-pop-dist {
            font-size: 0.88rem;
            color: #1e293b;
            font-weight: 500;
            margin-bottom: 6px;
          }
          .cpm-pop-countdown {
            font-size: 0.88rem;
            color: #0f766e;
            font-weight: 500;
            margin-bottom: 8px;
          }
          .cpm-pop-schedule {
            font-size: 0.82rem;
            color: #475569;
            margin-bottom: 10px;
            line-height: 1.4;
          }
          .cpm-pop-amenities {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 14px;
          }
          .cpm-amenity-tag {
            font-size: 0.75rem;
            font-weight: 600;
            background: #dcfce7;
            color: #166534;
            padding: 3px 8px;
            border-radius: 6px;
          }
          .cpm-pop-actions {
            display: flex;
            gap: 10px;
          }
          .cpm-btn {
            flex: 1;
            padding: 9px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            text-align: center;
            text-decoration: none;
            box-sizing: border-box;
            transition: all 0.2s ease;
          }
          .cpm-btn:hover {
            opacity: 0.9;
            transform: translateY(-1px);
          }
          .cpm-btn-primary {
            background: var(--cpm-teal);
            color: #ffffff;
            box-shadow: 0 2px 6px rgba(0, 162, 154, 0.3);
          }
          .cpm-btn-secondary {
            background: var(--cpm-teal);
            color: #ffffff;
            box-shadow: 0 2px 6px rgba(0, 162, 154, 0.3);
          }
          /* Blue pulsing user marker */
          @keyframes cpmPulse {
            0% { transform: scale(0.6); opacity: 0.9; }
            100% { transform: scale(2.4); opacity: 0; }
          }
        </style>
        <ha-card>
          <div class="cpm-header">
            <div class="cpm-title-row">
              <div class="cpm-title">
                <ha-icon icon="mdi:storefront" style="--mdc-icon-size: 24px; color: var(--cpm-teal);"></ha-icon>
                ${esc(this._config.title)}
              </div>
            </div>
            <div class="cpm-pills" id="targets-bar"></div>
          </div>
          <div class="cpm-filter-bar" id="filters-bar"></div>
          <div id="map"></div>
        </ha-card>
      `;

      // Attach ResizeObserver to keep leaflet crisp
      const mapEl = this.shadowRoot.getElementById("map");
      const ro = new ResizeObserver(() => {
        if (this._map) {
          this._map.invalidateSize();
        }
      });
      ro.observe(mapEl);
    }

    // Update target switcher pills
    const targetsBar = this.shadowRoot.getElementById("targets-bar");
    if (targetsBar) {
      targetsBar.innerHTML = targets
        .map(
          (tObj) => `
          <button class="cpm-pill ${tObj.attributes.target === this._selectedTarget ? "active" : ""}"
            data-target="${esc(tObj.attributes.target)}">
            <ha-icon icon="${tObj.attributes.target === "zone.home" ? "mdi:home-variant" : "mdi:account"}" style="--mdc-icon-size: 14px;"></ha-icon>
            ${esc(tObj.attributes.target_name || t.home)}
          </button>
        `
        )
        .join("");

      targetsBar.querySelectorAll(".cpm-pill").forEach((btn) => {
        btn.onclick = (e) => {
          const target = e.currentTarget.getAttribute("data-target");
          if (target && target !== this._selectedTarget) {
            this._selectedTarget = target;
            this._userInteracted = false;
            this._render();
          }
        };
      });
    }

    // Update filter bar
    const filtersBar = this.shadowRoot.getElementById("filters-bar");
    if (filtersBar) {
      filtersBar.innerHTML = `
        <button class="cpm-filter-btn ${this._filter === "today" ? "active" : ""}" data-filter="today">
          ${t.today} (${openTodayCount})
        </button>
        <button class="cpm-filter-btn ${this._filter === "open" ? "active" : ""}" data-filter="open">
          ${t.openNow} (${openNowCount})
        </button>
        <button class="cpm-filter-btn ${this._filter === "all" ? "active" : ""}" data-filter="all">
          ${t.all} (${allNearby.length})
        </button>
      `;

      filtersBar.querySelectorAll(".cpm-filter-btn").forEach((btn) => {
        btn.onclick = (e) => {
          const f = e.currentTarget.getAttribute("data-filter");
          if (f && f !== this._filter) {
            this._filter = f;
            this._render();
          }
        };
      });
    }

    // Initialize or update Map
    loadLeaflet().then((L) => {
      this._updateMap(L, displayedMarkets, originLat, originLon, t, lang);
    });
  }

  _updateMap(L, markets, originLat, originLon, t, lang) {
    const mapEl = this.shadowRoot.getElementById("map");
    if (!mapEl) return;

    if (!this._map) {
      const defaultLat = originLat || this._hass.config.latitude || 3.139;
      const defaultLon = originLon || this._hass.config.longitude || 101.6869;

      this._map = L.map(mapEl, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: true,
      }).setView([defaultLat, defaultLon], 13);

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        referrerPolicy: "strict-origin-when-cross-origin",
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> | CariPasarMalam',
      }).addTo(this._map);

      this._markersLayer = L.layerGroup().addTo(this._map);

      this._map.on("dragstart", () => {
        this._userInteracted = true;
      });
      this._map.on("zoomstart", () => {
        this._userInteracted = true;
      });
    }

    this._markersLayer.clearLayers();
    const bounds = [];

    // Add user/origin blue pulsing marker
    if (originLat != null && originLon != null) {
      const meIcon = L.divIcon({
        className: "cpm-me-icon",
        html: `
          <div style="position: relative; width: 22px; height: 22px;">
            <div style="
              position: absolute;
              inset: -4px;
              border-radius: 50%;
              background: rgba(37, 99, 235, 0.4);
              animation: cpmPulse 2s infinite ease-out;
            "></div>
            <div style="
              position: absolute;
              top: 3px; left: 3px;
              width: 16px; height: 16px;
              border-radius: 50%;
              background: #2563eb;
              border: 2.5px solid #ffffff;
              box-shadow: 0 2px 6px rgba(0,0,0,0.35);
            "></div>
          </div>
        `,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const meMarker = L.marker([originLat, originLon], { icon: meIcon }).addTo(this._markersLayer);
      meMarker.bindTooltip(t.currentLocation, { direction: "top", offset: [0, -10] });
      bounds.push([originLat, originLon]);
    }

    // Add market markers
    for (const m of markets) {
      if (m.latitude == null || m.longitude == null) continue;
      const mLat = Number(m.latitude);
      const mLon = Number(m.longitude);
      bounds.push([mLat, mLon]);

      const isOpen = m.status === "open";
      const isSoon = m.status === "opening_soon";

      // Dark blue-gray round pin matching pasarmalam.app screenshot
      const pinColor = isOpen ? "#10b981" : isSoon ? "#f59e0b" : "#334155";

      const pinIcon = L.divIcon({
        className: "cpm-market-pin",
        html: `
          <div style="
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: ${pinColor};
            border: 2.5px solid #ffffff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            cursor: pointer;
          ">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
            </svg>
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -16],
      });

      // Status pill HTML
      let statusClass = "cpm-status-closed";
      let statusText = t.closed;
      let countdownText = "";

      if (isOpen) {
        statusClass = "cpm-status-open";
        statusText = t.openNow;
        if (m.minutes_until_close) {
          countdownText = this._formatCountdown(m.minutes_until_close, true, t);
        }
      } else if (isSoon) {
        statusClass = "cpm-status-soon";
        statusText = t.openingSoon;
        if (m.minutes_until_next_open) {
          countdownText = this._formatCountdown(m.minutes_until_next_open, false, t);
        }
      } else if (m.minutes_until_next_open) {
        countdownText = this._formatCountdown(m.minutes_until_next_open, false, t);
      }

      const distStr = m.distance_km != null ? `${m.distance_km} km ${t.fromHere}` : "";
      const locStr = [m.district, m.state].filter(Boolean).join(", ");
      const scheduleStr = this._formatScheduleDays(m.schedule, lang, t);
      const directionsUrl = navUrl(mLat, mLon, m.name);
      const detailsUrl = m.gmaps_link || `https://www.google.com/maps/search/?api=1&query=${mLat},${mLon}`;

      const popupHtml = `
        <div class="cpm-popup">
          <div class="cpm-pop-top">
            <div class="cpm-pop-title">${esc(m.name)}</div>
            <span class="cpm-status-pill ${statusClass}">${statusText}</span>
          </div>
          ${locStr ? `<div class="cpm-pop-sub">${esc(locStr)}</div>` : ""}
          ${distStr ? `<div class="cpm-pop-dist">${distStr}</div>` : ""}
          ${countdownText ? `<div class="cpm-pop-countdown">${countdownText}</div>` : ""}
          ${scheduleStr ? `<div class="cpm-pop-schedule">${esc(scheduleStr)}</div>` : ""}
          <div class="cpm-pop-amenities">
            ${m.parking_available ? `<span class="cpm-amenity-tag">${t.parking}</span>` : ""}
            ${m.has_prayer_room ? `<span class="cpm-amenity-tag">${t.prayerRoom}</span>` : ""}
            ${m.has_toilet ? `<span class="cpm-amenity-tag">${t.toilet}</span>` : ""}
          </div>
          <div class="cpm-pop-actions">
            <a class="cpm-btn cpm-btn-primary" href="${directionsUrl}" target="_blank" rel="noopener noreferrer">
              ${t.getDirections}
            </a>
            <a class="cpm-btn cpm-btn-secondary" href="${detailsUrl}" target="_blank" rel="noopener noreferrer">
              ${t.viewDetails}
            </a>
          </div>
        </div>
      `;

      const marker = L.marker([mLat, mLon], { icon: pinIcon }).addTo(this._markersLayer);
      marker.bindPopup(popupHtml, { maxWidth: 320 });
    }

    // Auto-fit bounds if user hasn't panned/zoomed
    if (!this._userInteracted && bounds.length > 0) {
      if (bounds.length === 1) {
        this._map.setView(bounds[0], 14);
      } else {
        this._map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
      }
    }
  }
}

customElements.define("caripasarmalam-card", CariPasarMalamCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "caripasarmalam-card",
  name: "CariPasarMalam Map Card",
  description: "Interactive Leaflet map showing nearby night markets with live popups, hours, and navigation.",
  preview: true,
  documentationURL: "https://github.com/zubir2k/homeassistant-caripasarmalam",
});

console.info(
  `%c CARIPASARMALAM-MAP-CARD %c v${CARD_VERSION} `,
  "color: white; background: #0f172a; font-weight: 700;",
  "color: #ffffff; background: #00a29a; font-weight: 700;"
);
