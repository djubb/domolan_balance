"""DataUpdateCoordinator for the Domolan Balance integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DomolanApiClient, DomolanApiError, DomolanAuthError

_LOGGER = logging.getLogger(__name__)


class DomolanDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls domolan.ru for the account dashboard data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: DomolanApiClient,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Domolan Balance",
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_ensure_logged_in_and_get_balance()
        except DomolanAuthError as err:
            # Credentials no longer work (e.g. password changed) -> ask the
            # user to re-authenticate instead of retrying forever.
            raise ConfigEntryAuthFailed(str(err)) from err
        except DomolanApiError as err:
            raise UpdateFailed(str(err)) from err
