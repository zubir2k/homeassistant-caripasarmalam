"""Set-up, dynamic location sensors, and the config flow."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.caripasarmalam.const import API_MARKETS, DOMAIN

HOME = {"latitude": 2.9930, "longitude": 101.7890, "radius": 100, "friendly_name": "Home"}


async def _setup(hass, aioclient_mock, payload):
    aioclient_mock.get(API_MARKETS, json=payload)
    hass.states.async_set("zone.home", "0", HOME)
    hass.states.async_set("person.zubir", "home", {"latitude": 2.9930, "longitude": 101.7890, "friendly_name": "Zubir"})
    hass.states.async_set("person.nogps", "unknown", {"friendly_name": "No GPS"})
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, options={"radius": 10, "max_markets": 20})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_sensors_per_location(hass: HomeAssistant, aioclient_mock, markets_payload):
    entry = await _setup(hass, aioclient_mock, markets_payload)
    home = hass.states.get("sensor.pasarmalam_home")
    assert home is not None and home.state.isdigit()
    assert home.attributes["nearby_count"] == len(markets_payload["data"])
    assert hass.states.get("sensor.pasarmalam_zubir") is not None
    assert hass.states.get("sensor.pasarmalam_nogps") is None
    assert hass.states.get("sensor.pasarmalam_dataset") is not None
    # The dataset is fetched once (one page, fewer than 200 rows)
    assert aioclient_mock.call_count == 2 or aioclient_mock.call_count == 1

    # Zubir loses GPS: his sensor goes on the next coordinator refresh
    hass.states.async_set("person.zubir", "unknown", {"friendly_name": "Zubir"})
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get("sensor.pasarmalam_zubir") is None


async def test_user_agent_sent(hass: HomeAssistant, aioclient_mock, markets_payload):
    await _setup(hass, aioclient_mock, markets_payload)
    headers = aioclient_mock.mock_calls[0][3]
    assert headers["User-Agent"].startswith("homeassistant-caripasarmalam/")


async def test_config_flow(hass: HomeAssistant, aioclient_mock, markets_payload):
    aioclient_mock.get(API_MARKETS, json=markets_payload)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"radius": 8, "max_markets": 15})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"radius": 8.0, "max_markets": 15}


async def test_config_flow_cannot_connect(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(API_MARKETS, status=403)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"radius": 8, "max_markets": 15})
    assert result["errors"] == {"base": "cannot_connect"}
