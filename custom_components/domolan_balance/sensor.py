"""Sensor platform for the Domolan Balance integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, UnitOfDataRate, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_BLOCK_TYPE,
    ATTR_BLOCKED_BY_LOW_BALANCE,
    ATTR_CREDIT_BY_USER,
    ATTR_LOGIN,
    ATTR_MONTHLY_TRAFFIC,
    ATTR_NEXT_SPEED,
    ATTR_TARIFF_ACTIVE_SINCE,
    ATTR_TARIFF_ID,
    ATTR_TARIFF_PRICE,
    ATTR_TRAFFIC_LIMIT,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import DomolanDataUpdateCoordinator


def _current_tariff(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Look up the raw tariff object for the account's active tariffId.

    ``data["tariffs"]`` is a dict keyed by tariffId (as a string), each
    value carrying at least ``name``, ``price`` and a ``speed`` map, e.g.
    ``{"0": 100}`` for the base speed in Mbit/s.
    """
    if not data:
        return None
    tariff_id = data.get("tariffId")
    tariffs = data.get("tariffs")
    if tariff_id is None or not isinstance(tariffs, dict):
        return None
    return tariffs.get(str(tariff_id))


def _current_speed(data: dict[str, Any] | None) -> float | None:
    """Current effective speed in Mbit/s.

    Prefers ``tariffDetails.speed`` (accounts for e.g. traffic-based speed
    drops), falling back to the plain tariff's base speed.
    """
    if not data:
        return None
    tariff_details = data.get("tariffDetails") or {}
    speed = tariff_details.get("speed")
    if speed is None:
        tariff = _current_tariff(data)
        if tariff and isinstance(tariff.get("speed"), dict):
            speed = tariff["speed"].get("0")
    return speed


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Domolan Balance sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            DomolanBalanceSensor(coordinator, entry),
            DomolanDaysRemainingSensor(coordinator, entry),
            DomolanTariffSensor(coordinator, entry),
            DomolanSpeedSensor(coordinator, entry),
        ]
    )


class DomolanEntity(CoordinatorEntity[DomolanDataUpdateCoordinator], SensorEntity):
    """Common base: groups all sensors under one device per account."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DomolanDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        login = entry.data[CONF_USERNAME]
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Домолан ({login})",
            manufacturer=MANUFACTURER,
            entry_type="service",
        )


class DomolanBalanceSensor(DomolanEntity):
    """The subscriber's current account balance."""

    _attr_translation_key = "balance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "RUB"
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator: DomolanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "balance")

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data is None:
            return None
        balance = data.get("balance")
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


class DomolanDaysRemainingSensor(DomolanEntity):
    """How many days the current balance will last ("Хватит на N дней")."""

    _attr_translation_key = "days_remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: DomolanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "days_remaining")

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        if data is None:
            return None
        days = data.get("daysBeforeBlock")
        return int(days) if days is not None else None


class DomolanTariffSensor(DomolanEntity):
    """The name of the currently active tariff plan."""

    _attr_translation_key = "tariff"
    _attr_icon = "mdi:file-document-outline"

    def __init__(self, coordinator: DomolanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "tariff")

    @property
    def native_value(self) -> str | None:
        tariff = _current_tariff(self.coordinator.data)
        return tariff.get("name") if tariff else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        tariff = _current_tariff(data)
        if tariff is None:
            return None
        return {
            ATTR_TARIFF_ID: data.get("tariffId"),
            ATTR_TARIFF_PRICE: tariff.get("price"),
            ATTR_TARIFF_ACTIVE_SINCE: data.get("tariffActiveSince"),
        }


class DomolanSpeedSensor(DomolanEntity):
    """The current effective connection speed."""

    _attr_translation_key = "speed"
    _attr_device_class = SensorDeviceClass.DATA_RATE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfDataRate.MEGABITS_PER_SECOND
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: DomolanDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "speed")

    @property
    def native_value(self) -> float | None:
        speed = _current_speed(self.coordinator.data)
        return float(speed) if speed is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if data is None:
            return None
        tariff_details = data.get("tariffDetails") or {}
        return {
            ATTR_NEXT_SPEED: tariff_details.get("nextSpeed"),
            ATTR_TRAFFIC_LIMIT: tariff_details.get("currentTrafficLimit"),
            ATTR_MONTHLY_TRAFFIC: tariff_details.get("traffic"),
        }
