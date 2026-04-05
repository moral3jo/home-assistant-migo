"""Config flow for Saunier Duval MiGo."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MiGoAPI, MiGoAPIError, MiGoAuthError
from .const import (
    CONF_HOME_ID,
    CONF_HOME_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class MiGoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the MiGo config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._api: MiGoAPI | None = None
        self._homes: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            session = async_get_clientsession(self.hass)
            self._api = MiGoAPI(self._username, self._password, session)

            try:
                await self._api.authenticate()
                homes_data = await self._api.get_homes_data()
                self._homes = homes_data.get("body", {}).get("homes", [])
            except MiGoAuthError:
                errors["base"] = "invalid_auth"
            except MiGoAPIError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during MiGo setup")
                errors["base"] = "unknown"
            else:
                if not self._homes:
                    errors["base"] = "no_homes_found"
                elif len(self._homes) == 1:
                    return await self._create_entry(self._homes[0])
                else:
                    return await self.async_step_pick_home()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_pick_home(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose which home to configure when there are multiple."""
        if user_input is not None:
            home_id = user_input[CONF_HOME_ID]
            home = next((h for h in self._homes if h["id"] == home_id), None)
            if home:
                return await self._create_entry(home)

        home_options = {h["id"]: h.get("name", h["id"]) for h in self._homes}

        return self.async_show_form(
            step_id="pick_home",
            data_schema=vol.Schema(
                {vol.Required(CONF_HOME_ID): vol.In(home_options)}
            ),
        )

    async def _create_entry(self, home: dict) -> ConfigFlowResult:
        home_id = home["id"]
        home_name = home.get("name", "MiGo Home")

        await self.async_set_unique_id(home_id)
        self._abort_if_unique_id_configured()

        assert self._api is not None
        token_info = self._api.get_token_info()

        return self.async_create_entry(
            title=home_name,
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_HOME_ID: home_id,
                CONF_HOME_NAME: home_name,
                **token_info,
            },
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-authentication flow when credentials have expired."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = MiGoAPI(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], session)
            try:
                await api.authenticate()
            except MiGoAuthError:
                errors["base"] = "invalid_auth"
            except MiGoAPIError:
                errors["base"] = "cannot_connect"
            else:
                token_info = api.get_token_info()
                self.hass.config_entries.async_update_entry(
                    self._get_reauth_entry(),
                    data={
                        **self._get_reauth_entry().data,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        **token_info,
                    },
                )
                await self.hass.config_entries.async_reload(
                    self._get_reauth_entry().entry_id
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
