"""Config flow for CariPasarMalam integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    API_MARKETS_URL,
    CONF_HOME_RADIUS,
    CONF_PERSON_RADIUS,
    CONF_SCAN_INTERVAL,
    CONF_TRACKED_PERSONS,
    DEFAULT_HOME_RADIUS,
    DEFAULT_PERSON_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_RADIUS,
    MIN_RADIUS,
)

_LOGGER = logging.getLogger(__name__)


async def _async_can_reach_api(hass: HomeAssistant) -> bool:
    """Test if pasarmalam.app API is reachable."""
    try:
        session = async_get_clientsession(hass)
        async with session.get(f"{API_MARKETS_URL}?limit=1", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            return resp.status == 200
    except (aiohttp.ClientError, TimeoutError):
        return False


class CariPasarMalamConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CariPasarMalam."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            if await _async_can_reach_api(self.hass):
                return self.async_create_entry(
                    title="Cari Pasar Malam",
                    data=user_input,
                    options={},
                )
            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOME_RADIUS,
                    default=DEFAULT_HOME_RADIUS,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_RADIUS,
                        max=MAX_RADIUS,
                        step=1,
                        unit_of_measurement="km",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_PERSON_RADIUS,
                    default=DEFAULT_PERSON_RADIUS,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_RADIUS,
                        max=MAX_RADIUS,
                        step=1,
                        unit_of_measurement="km",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=1440,
                        step=5,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return CariPasarMalamOptionsFlow()


class CariPasarMalamOptionsFlow(OptionsFlow):
    """Handle options for CariPasarMalam."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the CariPasarMalam options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.config_entry
        current_home_radius = entry.options.get(
            CONF_HOME_RADIUS, entry.data.get(CONF_HOME_RADIUS, DEFAULT_HOME_RADIUS)
        )
        current_person_radius = entry.options.get(
            CONF_PERSON_RADIUS, entry.data.get(CONF_PERSON_RADIUS, DEFAULT_PERSON_RADIUS)
        )
        current_scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        current_tracked_persons = entry.options.get(
            CONF_TRACKED_PERSONS, entry.data.get(CONF_TRACKED_PERSONS, [])
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOME_RADIUS,
                    default=current_home_radius,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_RADIUS,
                        max=MAX_RADIUS,
                        step=1,
                        unit_of_measurement="km",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_PERSON_RADIUS,
                    default=current_person_radius,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_RADIUS,
                        max=MAX_RADIUS,
                        step=1,
                        unit_of_measurement="km",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_TRACKED_PERSONS,
                    default=current_tracked_persons,
                ): EntitySelector(
                    EntitySelectorConfig(
                        domain="person",
                        multiple=True,
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current_scan_interval,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=1440,
                        step=5,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
