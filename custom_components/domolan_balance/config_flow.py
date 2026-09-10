"""Config flow for the Domolan Balance integration."""
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
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .api import DomolanApiClient, DomolanApiError, DomolanAuthError
from .const import (
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _validate_credentials(login: str, password: str) -> None:
    """Try logging in with a throwaway session. Raises on failure."""
    async with aiohttp.ClientSession() as session:
        client = DomolanApiClient(session, login, password)
        await client.async_login()


class DomolanBalanceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Domolan Balance."""

    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            login = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(login)
            self._abort_if_unique_id_configured()

            try:
                await _validate_credentials(login, password)
            except DomolanAuthError:
                errors["base"] = "invalid_auth"
            except DomolanApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Domolan credentials")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=login,
                    data={CONF_USERNAME: login, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None

        if user_input is not None:
            login = self._reauth_entry.data[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                await _validate_credentials(login, password)
            except DomolanAuthError:
                errors["base"] = "invalid_auth"
            except DomolanApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Domolan credentials")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, CONF_PASSWORD: password},
                )
                await self.hass.config_entries.async_reload(
                    self._reauth_entry.entry_id
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={
                CONF_USERNAME: self._reauth_entry.data[CONF_USERNAME]
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return DomolanBalanceOptionsFlow()


class DomolanBalanceOptionsFlow(OptionsFlow):
    """Let the user tweak the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES, default=current
                ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
