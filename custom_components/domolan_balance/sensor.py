"""Sensor platform for the Domolan Balance integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_BLOCK_TYPE,
    ATTR_BLOCKED_BY_LOW_BALANCE,
    ATTR_CREDIT_BY_USER,
    ATTR_LOGIN,
    ATTR_TARIFF_ID,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import DomolanDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Domolan Balance sensor."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([DomolanBalanceSensor(coordinator, entry)])


class DomolanBalanceSensor(CoordinatorEntity[DomolanDataUpdateCoordinator], SensorEntity):
    """Represents the subscriber's current account balance."""

    _attr_has_entity_name = True
    _attr_translation_key = "balance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "RUB"
    _attr_icon = "mdi:cash"

    def __init__(
        self, coordinator: DomolanDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        login = entry.data[CONF_USERNAME]
        self._attr_unique_id = f"{entry.entry_id}_balance"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Домолан ({login})",
            manufacturer=MANUFACTURER,
            entry_type="service",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        balance = self.coordinator.data.get("balance")
        return float(balance) if balance is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if data is None:
            return None
        return {
            ATTR_LOGIN: data.get("login"),
            ATTR_TARIFF_ID: data.get("tariffId"),
            ATTR_BLOCKED_BY_LOW_BALANCE: data.get("blockedByLowBalance"),
            ATTR_BLOCK_TYPE: data.get("blockType"),
            ATTR_CREDIT_BY_USER: data.get("creditByUser"),
        }
