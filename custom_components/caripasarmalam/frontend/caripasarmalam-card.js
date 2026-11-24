/**
 * Cari Pasar Malam Card
 * Leaflet map + list of nearby markets for the Cari Pasar Malam integration
 * (https://github.com/zubir2k/homeassistant-caripasarmalam).
 *
 * Data: CariPasarMalam (https://pasarmalam.app), community maintained, MIT.
 * Map: Leaflet (BSD-2), bundled. Tiles: OpenStreetMap / CARTO.
 *
 * MIT License
 */

const CARD_VERSION = "0.1.0";
const TZ = "Asia/Kuala_Lumpur";
const BASE = new URL(".", import.meta.url).href; // .../caripasarmalam_static/
const LEAFLET_JS = `${BASE}leaflet/leaflet.js`;
const LEAFLET_CSS = `${BASE}leaflet/leaflet.css`;

const COLORS = {
  open: { fg: "#16a34a", ring: "rgba(22,163,74,.30)" },
  opening_soon: { fg: "#f59e0b", ring: "rgba(245,158,11,.35)" },
  closed: { fg: "#64748b", ring: "rgba(100,116,139,.24)" },
  unknown: { fg: "#94a3b8", ring: "rgba(148,163,184,.20)" },
};

const TILES = {
  light: {
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 20,
    referrerPolicy: "strict-origin-when-cross-origin",
  },
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 20,
    referrerPolicy: "strict-origin-when-cross-origin",
  },
};

const T = {
  ms: {
    title: "Pasar Berdekatan",
    open: "Dibuka",
    opening_soon: "Buka sekejap lagi",
    closed: "Tutup",
    unknown: "Tiada jadual",
    openNow: "dibuka sekarang",
    closesAt: "Tutup",
    closesIn: "Tutup dalam",
    opensIn: "Dibuka dalam",
    opensOn: "Dibuka",
    today: "Hari ini",
    away: "dari sini",
    directions: "Arah",
    details: "Butiran",
    parking: "Parkir",
    toilet: "Tandas",
    surau: "Surau",
    none: "Tiada pasar dalam radius",
    noSensor: "Sensor tidak dijumpai",
    loading: "Memuatkan peta...",
    home: "Rumah",
    midnight: "12 tengah malam",
    days: { mon: "Isnin", tue: "Selasa", wed: "Rabu", thu: "Khamis", fri: "Jumaat", sat: "Sabtu", sun: "Ahad" },
    h: "j",
    m: "m",
    d: "h",
  },
  en: {
    title: "Markets Nearby",
    open: "Open",
    opening_soon: "Opening soon",
    closed: "Closed",
    unknown: "No schedule",
    openNow: "open now",
    closesAt: "Closes",
    closesIn: "Closes in",
    opensIn: "Opens in",
    opensOn: "Opens",
    today: "Today",
    away: "away",
    directions: "Directions",
    details: "Details",
    parking: "Parking",
    toilet: "Toilet",
    surau: "Prayer room",
    none: "No markets within the radius",
    noSensor: "Sensor not found",
    loading: "Loading map...",
    home: "Home",
    midnight: "midnight",
    days: { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" },
    h: "h",
    m: "m",
    d: "d",
  },
};

let leafletPromise;
function loadLeaflet() {
  if (window.L && window.L.map) return Promise.resolve(window.L);
  if (!leafletPromise) {
    leafletPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = LEAFLET_JS;
      s.async = true;
      s.onload = () => resolve(window.L);
      s.onerror = () => {
        leafletPromise = undefined;
        reject(new Error("Leaflet failed to load"));
      };
      document.head.appendChild(s);
    });
  }
  return leafletPromise;
}

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class CariPasarMalamCard extends HTMLElement {
  static getStubConfig(hass) {
    const ids = Object.keys(hass?.states || {}).filter(
      (e) => e.startsWith("sensor.pasarmalam_") && e !== "sensor.pasarmalam_dataset"
    );
    const home = ids.find((e) => e === "sensor.pasarmalam_home");
    return { entities: home ? [home, ...ids.filter((e) => e !== home)] : ids.slice(0, 3) };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entities", selector: { entity: { multiple: true, filter: { integration: "caripasarmalam", domain: "sensor" } } } },
        { name: "title", selector: { text: {} } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "map_height", selector: { number: { min: 150, max: 800, step: 10, unit_of_measurement: "px", mode: "box" } } },
            { name: "list_limit", selector: { number: { min: 0, max: 50, step: 1, mode: "box" } } },
          ],
        },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "tiles", selector: { select: { options: ["auto", "light", "dark"], mode: "dropdown" } } },
            { name: "language", selector: { select: { options: ["auto", "ms", "en"], mode: "dropdown" } } },
          ],
        },
        { name: "show_closed", selector: { boolean: {} } },
        { name: "show_radius", selector: { boolean: {} } },
      ],
      computeLabel: (s) =>
        ({
          entities: "Locations",
          title: "Title",
          map_height: "Map height",
          list_limit: "Markets in list (0 hides the list)",
          tiles: "Map style",
          language: "Language",
          show_closed: "Show closed markets",
          show_radius: "Show search radius",
        })[s.name],
    };
  }

  setConfig(config) {
    const entities = config.entities || (config.entity ? [config.entity] : []);
    if (!entities.length) throw new Error("Add at least one sensor.pasarmalam_* entity");
    this._config = {
      map_height: 320,
      list_limit: 6,
      tiles: "auto",
      language: "auto",
      show_closed: true,
      show_radius: true,
      ...config,
      entities: entities.map((e) => (typeof e === "string" ? e : e.entity)),
    };
    this._active = this._config.entities[0];
    this._fitted = null;
    this._sig = null;
    if (this._map) {
      this._map.remove();
      this._map = null;
    }
    this._built = false;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return Math.ceil((this._config?.map_height || 320) / 50) + Math.min(this._config?.list_limit ?? 6, 6) + 1;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  connectedCallback() {
    if (this._map) setTimeout(() => this._map && this._map.invalidateSize(), 0);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = null;
  }

  /* ---------- helpers ---------- */

  get _t() {
    const pick = this._config.language;
    const lang = pick && pick !== "auto" ? pick : (this._hass?.locale?.language || this._hass?.language || "en");
    return lang.startsWith("ms") ? T.ms : T.en;
  }

  get _dark() {
    if (this._config.tiles === "dark") return true;
    if (this._config.tiles === "light") return false;
    return !!this._hass?.themes?.darkMode;
  }

  _dur(min) {
    const t = this._t;
    min = Math.max(0, Math.round(min));
    if (min >= 1440) {
      const d = Math.floor(min / 1440);
      const h = Math.floor((min % 1440) / 60);
      return h ? `${d}${t.d} ${h}${t.h}` : `${d}${t.d}`;
    }
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h ? `${h}${t.h} ${m}${t.m}` : `${m}${t.m}`;
  }

  _time(iso) {
    const hm = new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: TZ });
    if (hm === "00:00" || hm === "24:00") return this._t.midnight;
    const lang = this._t === T.ms ? "ms-MY" : "en-MY";
    return new Date(iso).toLocaleTimeString(lang, { hour: "numeric", minute: "2-digit", timeZone: TZ });
  }

  _weekday(iso) {
    const code = new Date(iso).toLocaleDateString("en-US", { weekday: "short", timeZone: TZ }).toLowerCase().slice(0, 3);
    return this._t.days[code] || code;
  }

  /** Live status text from the ISO times, so it stays right between sensor updates. */
  _when(m) {
    const t = this._t;
    const now = Date.now();
    if (m.status === "open" && m.closes_at) {
      const left = (new Date(m.closes_at) - now) / 60000;
      return left <= 120 ? `${t.closesIn} ${this._dur(left)}` : `${t.closesAt} ${this._time(m.closes_at)}`;
    }
    if (m.opens_at) {
      const wait = (new Date(m.opens_at) - now) / 60000;
      if (wait < 24 * 60) return `${t.opensIn} ${this._dur(wait)}`;
      return `${t.opensOn} ${this._weekday(m.opens_at)} ${this._time(m.opens_at)}`;
    }
    return t.unknown;
  }

  _km(d) {
    return d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`;
  }

  _markets(st) {
    const all = st?.attributes?.markets || [];
    return this._config.show_closed ? all : all.filter((m) => m.status === "open" || m.status === "opening_soon");
  }

  /* ---------- render ---------- */

  _shell() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const h = Number(this._config.map_height) || 320;
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="${LEAFLET_CSS}">
      <style>${STYLE}</style>
      <ha-card>
        <div class="head">
          <div class="title"></div>
          <div class="count"></div>
        </div>
        <div class="tabs"></div>
        <div class="mapwrap" style="height:${h}px">
          <div class="map"></div>
          <div class="loading">${esc(this._t.loading)}</div>
        </div>
        <div class="list"></div>
        <div class="foot">Data: <a href="https://pasarmalam.app" target="_blank" rel="noopener">CariPasarMalam</a></div>
      </ha-card>`;
    this._el = {
      title: this.shadowRoot.querySelector(".title"),
      count: this.shadowRoot.querySelector(".count"),
      tabs: this.shadowRoot.querySelector(".tabs"),
      map: this.shadowRoot.querySelector(".map"),
      loading: this.shadowRoot.querySelector(".loading"),
      list: this.shadowRoot.querySelector(".list"),
    };
    this._el.tabs.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-entity]");
      if (!b) return;
      this._active = b.dataset.entity;
      this._fitted = null;
      this._sig = null;
      this._render();
    });
    this._el.list.addEventListener("click", (ev) => {
      const row = ev.target.closest("[data-id]");
      if (!row || ev.target.closest("a")) return;
      const mk = this._markers?.[row.dataset.id];
      if (mk && this._map) {
        this._map.closePopup();
        this._map.once("moveend", () => mk.openPopup());
        this._map.flyTo(mk.getLatLng(), Math.max(this._map.getZoom(), 15), { duration: 0.6 });
      }
    });
    this._built = true;
    this._initMap();
    clearInterval(this._timer);
    this._timer = setInterval(() => {
      this._sig = null;
      this._render();
    }, 60000);
  }

  async _initMap() {
    try {
      const L = await loadLeaflet();
      if (this._map || !this._el) return;
      this._map = L.map(this._el.map, { zoomControl: true, attributionControl: true, scrollWheelZoom: false });
      this._tileDark = null;
      this._layer = L.layerGroup().addTo(this._map);
      this._map.setView([3.139, 101.6869], 11); // KL until we know better
      this._map.on("focus", () => this._map.scrollWheelZoom.enable());
      this._map.on("blur", () => this._map.scrollWheelZoom.disable());
      new ResizeObserver(() => {
        if (!this._map) return;
        this._map.invalidateSize();
        // A card built while hidden (another view, a closed tab) fits once it gets a size
        if (this._fitted !== this._active) {
          this._sig = null;
          this._render();
        }
      }).observe(this._el.map);
      this._el.loading.remove();
      this._sig = null;
      this._render();
    } catch (e) {
      if (this._el?.loading) this._el.loading.textContent = String(e.message || e);
    }
  }

  _setTiles(L) {
    const dark = this._dark;
    if (this._tiles && this._tileDark === dark) return;
    if (this._tiles) this._map.removeLayer(this._tiles);
    const cfg = dark ? TILES.dark : TILES.light;
    this._tiles = L.tileLayer(cfg.url, cfg).addTo(this._map);
    this._tileDark = dark;
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this._built) this._shell();
    const t = this._t;
    const hass = this._hass;
    const st = hass.states[this._active];

    // tabs
    const ents = this._config.entities;
    this._el.tabs.style.display = ents.length > 1 ? "" : "none";
    if (ents.length > 1) {
      this._el.tabs.innerHTML = ents
        .map((e) => {
          const s = hass.states[e];
          const name = e === "sensor.pasarmalam_home" ? t.home : s?.attributes?.friendly_name?.replace(/^Cari Pasar Malam\s*/i, "") || e;
          const n = s && !isNaN(Number(s.state)) ? Number(s.state) : 0;
          return `<button class="tab ${e === this._active ? "on" : ""}" data-entity="${esc(e)}">${esc(name)}${n ? ` <b>${n}</b>` : ""}</button>`;
        })
        .join("");
    }

    this._el.title.textContent = this._config.title || t.title;
    if (!st) {
      this._el.count.textContent = "";
      this._el.list.innerHTML = `<div class="empty">${esc(t.noSensor)}: ${esc(this._active)}</div>`;
      return;
    }
    const open = Number(st.state) || 0;
    this._el.count.innerHTML = open
      ? `<span class="dot open"></span>${open} ${esc(t.openNow)}`
      : `<span class="dot closed"></span>${esc(t.closed)}`;

    // Skip map/list work when nothing changed (hass updates arrive constantly)
    const sig = `${st.last_updated}|${this._active}|${this._dark}|${this._config.show_closed}`;
    if (sig === this._sig) return;
    this._sig = sig;

    const markets = this._markets(st);
    this._renderList(markets);
    if (this._map) this._renderMap(st, markets);
  }

  _renderList(markets) {
    const t = this._t;
    const limit = Number(this._config.list_limit ?? 6);
    if (limit <= 0) {
      this._el.list.innerHTML = "";
      return;
    }
    if (!markets.length) {
      this._el.list.innerHTML = `<div class="empty">${esc(t.none)}</div>`;
      return;
    }
    this._el.list.innerHTML = markets
      .slice(0, limit)
      .map(
        (m) => `
        <div class="row" data-id="${esc(m.id)}">
          <span class="dot ${esc(m.status)}"></span>
          <div class="info">
            <div class="name">${esc(m.name)}</div>
            <div class="sub">${esc(this._when(m))} · ${esc(this._km(m.distance_km))}</div>
          </div>
          <a class="go" href="${esc(this._dirUrl(m))}" target="_blank" rel="noopener" title="${esc(t.directions)}">
            <ha-icon icon="mdi:directions"></ha-icon>
          </a>
        </div>`
      )
      .join("");
  }

  _dirUrl(m) {
    return `https://www.google.com/maps/dir/?api=1&destination=${m.latitude},${m.longitude}`;
  }

  _popup(m) {
    const t = this._t;
    const c = COLORS[m.status] || COLORS.closed;
    const chips = [m.parking && t.parking, m.toilet && t.toilet, m.prayer_room && t.surau]
      .filter(Boolean)
      .map((x) => `<span class="chip">${esc(x)}</span>`)
      .join("");
    const days = (m.days || []).map((d) => t.days[d] || d).join(", ");
    const today = (m.today || []).length ? `${t.today}: ${m.today.join(", ")}` : days;
    return `
      <div class="pop">
        <div class="ptop"><b>${esc(m.name)}</b>
          <span class="badge" style="color:${c.fg};background:${c.ring}">${esc(t[m.status] || m.status)}</span></div>
        <div class="pl">${esc([m.district, m.state].filter(Boolean).join(", "))}</div>
        <div class="pl">${esc(this._km(m.distance_km))} ${esc(t.away)}</div>
        <div class="pl">${esc(this._when(m))}</div>
        ${today ? `<div class="pl muted">${esc(today)}</div>` : ""}
        ${chips ? `<div class="chips">${chips}</div>` : ""}
        <div class="btns">
          <a href="${esc(this._dirUrl(m))}" target="_blank" rel="noopener">${esc(t.directions)}</a>
          <a href="${esc(m.url || `https://pasarmalam.app/markets/${m.id}`)}" target="_blank" rel="noopener">${esc(t.details)}</a>
        </div>
      </div>`;
  }

  _renderMap(st, markets) {
    const L = window.L;
    this._setTiles(L);
    const openPopup = this._openId;
    this._layer.clearLayers();
    this._markers = {};

    const origin = st.attributes.origin;
    const radius = Number(st.attributes.radius_km) || 0;
    const pts = [];

    if (origin) {
      const src = this._hass.states[st.attributes.source];
      const pic = src?.attributes?.entity_picture;
      const icon = pic
        ? L.divIcon({ className: "", html: `<div class="me pic" style="background-image:url('${esc(pic)}')"></div>`, iconSize: [30, 30], iconAnchor: [15, 15] })
        : L.divIcon({ className: "", html: `<div class="me"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] });
      L.marker(origin, { icon, interactive: false, zIndexOffset: 1000 }).addTo(this._layer);
      if (this._config.show_radius && radius) {
        L.circle(origin, { radius: radius * 1000, color: "#3b82f6", weight: 1, dashArray: "4 4", fillOpacity: 0.04, interactive: false }).addTo(this._layer);
      }
      pts.push(origin);
    }

    for (const m of markets) {
      const c = COLORS[m.status] || COLORS.closed;
      const pulse = m.status === "open" ? " pulse" : "";
      const icon = L.divIcon({
        className: "",
        html: `<div class="pin${pulse}" style="--fg:${c.fg};--ring:${c.ring}"><span></span></div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
        popupAnchor: [0, -12],
      });
      const z = { open: 600, opening_soon: 500, closed: 300, unknown: 200 }[m.status] || 0;
      const mk = L.marker([m.latitude, m.longitude], { icon, title: m.name, zIndexOffset: z })
        .bindPopup(this._popup(m), { maxWidth: 280, className: "cpm" })
        .addTo(this._layer);
      mk.on("popupopen", () => (this._openId = m.id));
      mk.on("popupclose", () => {
        if (this._openId === m.id) this._openId = null;
      });
      this._markers[m.id] = mk;
      pts.push([m.latitude, m.longitude]);
    }

    // Fit once per location; afterwards leave the user's pan/zoom alone
    this._map.invalidateSize();
    const sized = this._el.map.clientWidth > 0 && this._el.map.clientHeight > 0;
    if (sized && this._fitted !== this._active && pts.length) {
      if (origin && radius && this._config.show_radius) {
        this._map.fitBounds(L.latLng(origin).toBounds(radius * 2000), { padding: [10, 10], animate: false });
      } else if (pts.length > 1) {
        this._map.fitBounds(L.latLngBounds(pts), { padding: [24, 24], maxZoom: 15, animate: false });
      } else {
        this._map.setView(pts[0], 14, { animate: false });
      }
      this._fitted = this._active;
    }
    if (openPopup && this._markers[openPopup]) this._markers[openPopup].openPopup();
  }
}

const STYLE = `
  :host { display:block; }
  ha-card { overflow:hidden; }
  .head { display:flex; align-items:center; justify-content:space-between; padding:14px 16px 8px; gap:8px; }
  .title { font-size:1.15em; font-weight:500; color:var(--primary-text-color); }
  .count { font-size:.9em; color:var(--secondary-text-color); display:flex; align-items:center; gap:6px; white-space:nowrap; }
  .tabs { display:flex; gap:6px; padding:0 16px 10px; overflow-x:auto; scrollbar-width:none; }
  .tab { border:1px solid var(--divider-color); background:none; color:var(--primary-text-color); border-radius:16px; padding:4px 12px; font:inherit; font-size:.85em; cursor:pointer; white-space:nowrap; }
  .tab.on { background:var(--primary-color); border-color:var(--primary-color); color:var(--text-primary-color, #fff); }
  .tab b { font-weight:600; margin-left:2px; }
  .mapwrap { position:relative; }
  .map { position:absolute; inset:0; z-index:0; background:var(--secondary-background-color); }
  .loading { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:var(--secondary-text-color); }
  .list { padding:4px 0; }
  .row { display:flex; align-items:center; gap:12px; padding:8px 16px; cursor:pointer; }
  .row:hover { background:var(--secondary-background-color); }
  .info { flex:1; min-width:0; }
  .name { color:var(--primary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .sub { color:var(--secondary-text-color); font-size:.85em; }
  .go { color:var(--primary-color); display:flex; }
  .empty { padding:12px 16px; color:var(--secondary-text-color); }
  .foot { padding:4px 16px 10px; font-size:.75em; color:var(--secondary-text-color); text-align:right; }
  .foot a { color:inherit; }
  .dot { width:10px; height:10px; border-radius:50%; flex:none; display:inline-block; }
  .dot.open { background:#16a34a; } .dot.opening_soon { background:#f59e0b; }
  .dot.closed { background:#64748b; } .dot.unknown { background:#94a3b8; }

  .pin { width:26px; height:26px; border-radius:50%; background:var(--ring); display:flex; align-items:center; justify-content:center; position:relative; }
  .pin span { width:14px; height:14px; border-radius:50%; background:var(--fg); border:2px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,.35); }
  .pin.pulse::after { content:""; position:absolute; inset:0; border-radius:50%; background:var(--ring); animation:pulse 2s ease-out infinite; }
  @keyframes pulse { from { transform:scale(1); opacity:.9; } to { transform:scale(2.2); opacity:0; } }
  .me { width:16px; height:16px; border-radius:50%; background:#3b82f6; border:3px solid #fff; box-shadow:0 0 0 2px rgba(59,130,246,.35), 0 1px 4px rgba(0,0,0,.4); box-sizing:border-box; }
  .me.pic { width:30px; height:30px; background-size:cover; background-position:center; border-width:2px; }

  .cpm .leaflet-popup-content-wrapper { border-radius:12px; }
  .cpm .leaflet-popup-content { margin:12px 14px; font-family:var(--paper-font-body1_-_font-family, inherit); }
  .pop { font-size:13px; line-height:1.45; color:#1f2937; }
  .ptop { padding-right:14px; display:flex; justify-content:space-between; gap:10px; align-items:flex-start; margin-bottom:6px; }
  .ptop b { font-size:14px; }
  .badge { font-size:11px; font-weight:600; padding:2px 8px; border-radius:999px; white-space:nowrap; }
  .pl { margin:2px 0; } .muted { color:#6b7280; }
  .chips { display:flex; gap:4px; flex-wrap:wrap; margin-top:6px; }
  .chip { background:#dcfce7; color:#166534; font-size:11px; padding:1px 6px; border-radius:4px; }
  .btns { display:flex; gap:6px; margin-top:10px; }
  .btns a { background:#0d9488; color:#fff !important; text-decoration:none; padding:5px 10px; border-radius:6px; font-size:12px; font-weight:500; }
`;

if (!customElements.get("caripasarmalam-card")) {
  customElements.define("caripasarmalam-card", CariPasarMalamCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "caripasarmalam-card",
    name: "Cari Pasar Malam",
    description: "Map and list of pasar malam near Home and each person",
    preview: false,
    documentationURL: "https://github.com/zubir2k/homeassistant-caripasarmalam",
  });
  console.info(`%c CARI-PASAR-MALAM-CARD %c v${CARD_VERSION} `, "color:#fff;background:#0d9488;font-weight:700", "color:#0d9488;background:#fff");
}
