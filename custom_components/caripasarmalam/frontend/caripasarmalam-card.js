/**
 * CariPasarMalam Card for Home Assistant
 * A vibrant Lovelace card to browse nearby night markets (pasar malam),
 * check operating hours, amenities, and navigate directly via Google Maps.
 *
 * MIT License
 */

const CARD_VERSION = "0.1.0";

const T = {
  en: {
    title: "Cari Pasar Malam",
    home: "Home",
    openNow: "Open Now",
    openingSoon: "Opening Soon",
    closed: "Closed Today",
    noneToday: "No pasar malam open today within radius",
    todayMarkets: "Markets Open Today",
    weeklySchedule: "Weekly Schedule",
    distance: "away",
    hours: "Hours",
    navigate: "Navigate",
    parking: "Parking",
    toilet: "Toilet",
    prayerRoom: "Surau",
    available: "Yes",
    unavailable: "None",
    noSensor: "No CariPasarMalam sensors found in Home Assistant.",
    allStates: "All Markets",
    days: {
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
    openNow: "Buka Sekarang",
    openingSoon: "Akan Buka",
    closed: "Tutup Hari Ini",
    noneToday: "Tiada pasar malam buka hari ini dalam lingkungan",
    todayMarkets: "Pasar Malam Hari Ini",
    weeklySchedule: "Jadual Mingguan",
    distance: "jauh",
    hours: "Waktu",
    navigate: "Pandu Arah",
    parking: "Parkir",
    toilet: "Tandas",
    prayerRoom: "Surau",
    available: "Ada",
    unavailable: "Tiada",
    noSensor: "Tiada sensor CariPasarMalam ditemui dalam Home Assistant.",
    allStates: "Semua Pasar Malam",
    days: {
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

class CariPasarMalamCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selectedTarget = null;
    this._activeTab = "today"; // "today" | "weekly"
  }

  setConfig(config) {
    this._config = {
      title: config.title || "Cari Pasar Malam",
      entity: config.entity,
      show_weekly: config.show_weekly !== false,
      language: config.language || "auto",
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
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

  _render() {
    if (!this._hass || !this.shadowRoot) return;

    const lang = this._getLang();
    const t = T[lang] || T.en;
    const targets = this._getTargetEntities();

    if (!targets.length) {
      this.shadowRoot.innerHTML = `
        <ha-card style="padding: 16px; text-align: center; color: var(--secondary-text-color);">
          <ha-icon icon="mdi:store-off" style="--mdc-icon-size: 36px; margin-bottom: 8px;"></ha-icon>
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
    const nearestName = currentSensor.state;
    const hasMarketToday = nearestName && nearestName !== "None open today" && nearestName !== "No GPS coordinates";
    const status = attrs.status || "closed";
    const distanceKm = attrs.distance_km;
    const hours = attrs.operating_hours_today;
    const address = attrs.address;
    const gmapsLink = attrs.gmaps_link;
    const lat = attrs.latitude;
    const lon = attrs.longitude;
    const marketsToday = attrs.markets_today || [];
    const openTodayCount = attrs.open_today_count || 0;
    const radiusKm = attrs.radius_km || 10;

    let statusBadgeClass = "badge-closed";
    let statusBadgeText = t.closed;
    if (status === "open") {
      statusBadgeClass = "badge-open";
      statusBadgeText = t.openNow;
    } else if (status === "opening_soon") {
      statusBadgeClass = "badge-soon";
      statusBadgeText = `${t.openingSoon} (${attrs.minutes_until_next_open || 0}m)`;
    }

    // Styles
    const style = `
      <style>
        ha-card {
          overflow: hidden;
          background: var(--card-background-color, #fff);
          border-radius: var(--ha-card-border-radius, 16px);
          font-family: var(--paper-font-body1_-_font-family, inherit);
          box-shadow: var(--ha-card-box-shadow, 0 4px 12px rgba(0, 0, 0, 0.08));
        }
        .header-bg {
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          color: #fff;
          padding: 16px 20px;
          position: relative;
        }
        .header-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .title {
          font-size: 1.15rem;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 8px;
          letter-spacing: -0.01em;
        }
        .target-pills {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          margin-top: 4px;
        }
        .target-pill {
          padding: 5px 12px;
          border-radius: 9999px;
          font-size: 0.8rem;
          font-weight: 600;
          background: rgba(255, 255, 255, 0.12);
          color: rgba(255, 255, 255, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.15);
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .target-pill.active {
          background: #f59e0b;
          color: #1e293b;
          border-color: #f59e0b;
          box-shadow: 0 2px 8px rgba(245, 158, 11, 0.4);
        }
        .hero {
          margin-top: 14px;
          padding: 14px;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          backdrop-filter: blur(8px);
          border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .hero-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 6px;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 8px;
          border-radius: 6px;
          font-size: 0.72rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .badge-open {
          background: #10b981;
          color: #fff;
        }
        .badge-soon {
          background: #f59e0b;
          color: #1e293b;
        }
        .badge-closed {
          background: rgba(255, 255, 255, 0.2);
          color: rgba(255, 255, 255, 0.8);
        }
        .hero-name {
          font-size: 1.25rem;
          font-weight: 700;
          margin: 4px 0;
          color: #fff;
        }
        .hero-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.85);
          margin-top: 6px;
        }
        .hero-meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .hero-address {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.7);
          margin-top: 8px;
          line-height: 1.3;
        }
        .btn-nav {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin-top: 10px;
          padding: 7px 14px;
          border-radius: 8px;
          background: #3b82f6;
          color: #fff;
          text-decoration: none;
          font-size: 0.85rem;
          font-weight: 600;
          transition: background 0.2s ease;
        }
        .btn-nav:hover {
          background: #2563eb;
        }
        .body-section {
          padding: 16px 20px;
        }
        .tabs {
          display: flex;
          border-bottom: 2px solid var(--divider-color, #e2e8f0);
          margin-bottom: 14px;
        }
        .tab {
          padding: 8px 16px;
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--secondary-text-color, #64748b);
          cursor: pointer;
          border-bottom: 2px solid transparent;
          margin-bottom: -2px;
          transition: all 0.2s ease;
        }
        .tab.active {
          color: #f59e0b;
          border-color: #f59e0b;
        }
        .market-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .market-card {
          padding: 12px 14px;
          border-radius: 10px;
          border: 1px solid var(--divider-color, #e2e8f0);
          background: var(--card-background-color, #fff);
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .market-card:hover {
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        .market-info {
          flex: 1;
        }
        .market-title {
          font-weight: 600;
          font-size: 0.95rem;
          color: var(--primary-text-color, #1e293b);
          margin-bottom: 3px;
        }
        .market-sub {
          font-size: 0.8rem;
          color: var(--secondary-text-color, #64748b);
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .dist-badge {
          background: rgba(245, 158, 11, 0.15);
          color: #b45309;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.75rem;
        }
        .icon-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--secondary-background-color, #f1f5f9);
          color: var(--primary-text-color, #1e293b);
          text-decoration: none;
          transition: background 0.2s ease;
        }
        .icon-btn:hover {
          background: #e2e8f0;
        }
        .empty-state {
          text-align: center;
          padding: 24px 16px;
          color: var(--secondary-text-color, #64748b);
          font-size: 0.9rem;
        }
      </style>
    `;

    // Render target pills
    const targetPillsHtml = targets
      .map(
        (tObj) => `
        <button class="target-pill ${tObj.attributes.target === this._selectedTarget ? "active" : ""}"
          data-target="${esc(tObj.attributes.target)}">
          <ha-icon icon="${tObj.attributes.target === "zone.home" ? "mdi:home-variant" : "mdi:account"}" style="--mdc-icon-size: 14px;"></ha-icon>
          ${esc(tObj.attributes.target_name || t.home)}
        </button>
      `
      )
      .join("");

    // Render Hero Market
    let heroHtml = "";
    if (hasMarketToday) {
      const navHref = lat && lon ? navUrl(lat, lon, nearestName) : gmapsLink || "#";
      heroHtml = `
        <div class="hero">
          <div class="hero-header">
            <span class="badge ${statusBadgeClass}">${statusBadgeText}</span>
            <span style="font-size: 0.8rem; font-weight: 600; color: #f59e0b;">
              ${distanceKm ? `${distanceKm} km ${t.distance}` : ""}
            </span>
          </div>
          <div class="hero-name">${esc(nearestName)}</div>
          <div class="hero-meta">
            ${hours ? `<div class="hero-meta-item"><ha-icon icon="mdi:clock-outline" style="--mdc-icon-size: 16px;"></ha-icon> ${esc(hours)}</div>` : ""}
            ${attrs.parking_available ? `<div class="hero-meta-item"><ha-icon icon="mdi:parking" style="--mdc-icon-size: 16px;"></ha-icon> ${t.parking}</div>` : ""}
            ${attrs.has_prayer_room ? `<div class="hero-meta-item"><ha-icon icon="mdi:mosque" style="--mdc-icon-size: 16px;"></ha-icon> ${t.prayerRoom}</div>` : ""}
          </div>
          ${address ? `<div class="hero-address">${esc(address)}</div>` : ""}
          <a class="btn-nav" href="${navHref}" target="_blank" rel="noopener noreferrer">
            <ha-icon icon="mdi:navigation" style="--mdc-icon-size: 16px;"></ha-icon>
            ${t.navigate}
          </a>
        </div>
      `;
    } else {
      heroHtml = `
        <div class="hero" style="text-align: center; padding: 20px;">
          <ha-icon icon="mdi:store-off" style="--mdc-icon-size: 32px; opacity: 0.6; margin-bottom: 6px;"></ha-icon>
          <div style="font-weight: 600; font-size: 0.95rem;">${t.noneToday}</div>
          <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 4px;">Radius: ${radiusKm} km</div>
        </div>
      `;
    }

    // Render Markets Today List
    let listHtml = "";
    if (marketsToday.length > 0) {
      listHtml = marketsToday
        .map((m) => {
          const mNav = m.latitude && m.longitude ? navUrl(m.latitude, m.longitude, m.name) : m.gmaps_link || "#";
          return `
          <div class="market-card">
            <div class="market-info">
              <div class="market-title">${esc(m.name)}</div>
              <div class="market-sub">
                <span class="dist-badge">${m.distance_km} km</span>
                ${m.operating_hours ? `<span>⏰ ${esc(m.operating_hours)}</span>` : ""}
                ${m.status === "open" ? `<span style="color: #10b981; font-weight: 600;">● ${t.openNow}</span>` : ""}
              </div>
            </div>
            <a class="icon-btn" href="${mNav}" target="_blank" rel="noopener noreferrer" title="${t.navigate}">
              <ha-icon icon="mdi:directions" style="--mdc-icon-size: 20px;"></ha-icon>
            </a>
          </div>
        `;
        })
        .join("");
    } else {
      listHtml = `<div class="empty-state">${t.noneToday}</div>`;
    }

    this.shadowRoot.innerHTML = `
      ${style}
      <ha-card>
        <div class="header-bg">
          <div class="header-top">
            <div class="title">
              <ha-icon icon="mdi:storefront" style="--mdc-icon-size: 24px; color: #f59e0b;"></ha-icon>
              ${esc(this._config.title)}
            </div>
          </div>
          <div class="target-pills">
            ${targetPillsHtml}
          </div>
          ${heroHtml}
        </div>
        <div class="body-section">
          <div class="tabs">
            <div class="tab active">${t.todayMarkets} (${openTodayCount})</div>
          </div>
          <div class="market-list">
            ${listHtml}
          </div>
        </div>
      </ha-card>
    `;

    // Attach click listeners to target pills
    this.shadowRoot.querySelectorAll(".target-pill").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const target = e.currentTarget.getAttribute("data-target");
        if (target && target !== this._selectedTarget) {
          this._selectedTarget = target;
          this._render();
        }
      });
    });
  }
}

customElements.define("caripasarmalam-card", CariPasarMalamCard);

// Register in Home Assistant's Custom Card Picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "caripasarmalam-card",
  name: "CariPasarMalam Card",
  description: "Browse nearby night markets (pasar malam) with opening times, distances, and directions.",
  preview: true,
  documentationURL: "https://github.com/zubir2k/homeassistant-caripasarmalam",
});

console.info(
  `%c CARIPASARMALAM-CARD %c v${CARD_VERSION} `,
  "color: white; background: #0f172a; font-weight: 700;",
  "color: #1e293b; background: #f59e0b; font-weight: 700;"
);
