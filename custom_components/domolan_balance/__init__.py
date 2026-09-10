"""The Domolan Balance integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .api import DomolanApiClient
from .const import CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
from .coordinator import DomolanDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class DomolanRuntimeData:
    """Runtime data stored on the config entry."""

    session: aiohttp.ClientSession
    coordinator: DomolanDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Domolan Balance from a config entry."""
    # A dedicated session (own cookie jar) per account, so multiple Domolan
    # accounts configured in the same HA instance don't share sails.sid.
    session = aiohttp.ClientSession()

    client = DomolanApiClient(
        session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    scan_interval_minutes = entry.options.get(
        CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
    )
    coordinator = DomolanDataUpdateCoordinator(
        hass, entry, client, timedelta(minutes=scan_interval_minutes)
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = DomolanRuntimeData(session=session, coordinator=coordinator)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.session.close()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options (e.g. scan interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)
