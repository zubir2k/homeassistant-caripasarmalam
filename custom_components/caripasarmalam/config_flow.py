"""Config flow for Cari Pasar Malam."""
from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.loader import async_get_integration

from .const import (
    API_MARKETS,
    CONF_MAX_MARKETS,
    CONF_RADIUS,
    DEFAULT_MAX_MARKETS,
    DEFAULT_RADIUS,
    DOMAIN,
    MAX_MAX_MARKETS,
    MAX_RADIUS,
    MIN_MAX_MARKETS,
    MIN_RADIUS,
    NAME,
    USER_AGENT,
)


def _schema(radius: float, max_markets: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_RADIUS, default=radius): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_RADIUS, max=MAX_RADIUS, step=1,
                    unit_of_measurement="km", mode=NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(CONF_MAX_MARKETS, default=max_markets): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_MAX_MARKETS, max=MAX_MAX_MARKETS, step=1, mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_RADIUS: float(user_input[CONF_RADIUS]),
        CONF_MAX_MARKETS: int(user_input[CONF_MAX_MARKETS]),
    }


async def _async_can_reach(hass: HomeAssistant) -> bool:
    integration = await async_get_integration(hass, DOMAIN)
    headers = {"User-Agent": USER_AGENT.format(version=integration.version or "0")}
    try:
        async with async_get_clientsession(hass).get(
            API_MARKETS, params={"limit": 1}, headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return False
            body = await resp.json(content_type=None)
            return isinstance(body, dict) and "data" in body
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return False


class CariPasarMalamConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry covers zone.home and every person with GPS."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            if await _async_can_reach(self.hass):
                return self.async_create_entry(title=NAME, data={}, options=_clean(user_input))
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(
                (user_input or {}).get(CONF_RADIUS, DEFAULT_RADIUS),
                (user_input or {}).get(CONF_MAX_MARKETS, DEFAULT_MAX_MARKETS),
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CariPasarMalamOptionsFlow()


class CariPasarMalamOptionsFlow(OptionsFlow):
    """Change the radius and list size without re-adding the integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_clean(user_input))
        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                opts.get(CONF_RADIUS, DEFAULT_RADIUS),
                opts.get(CONF_MAX_MARKETS, DEFAULT_MAX_MARKETS),
            ),
        )
