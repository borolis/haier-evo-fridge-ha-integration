"""Support for Haier Evo Fridge sensors."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HaierFridgeEntity
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Haier Evo Fridge sensor platform."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        HaierFridgeTemperatureSensor(device, "fridge", "Fridge Temperature"),
        HaierFridgeTemperatureSensor(device, "freezer", "Freezer Temperature"),
        HaierFridgeTemperatureSensor(device, "ambient", "Ambient Temperature"),
    ]

    async_add_entities(entities)


class HaierFridgeTemperatureSensor(HaierFridgeEntity, SensorEntity):
    """Haier Evo Fridge temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device, sensor_type, name) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self._sensor_type = sensor_type
        self._attr_name = f"{name}"
        self._attr_unique_id = f"{self._device.unique_id}_{sensor_type}_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self._sensor_type == "fridge":
            return self._device.fridge_temperature
        elif self._sensor_type == "freezer":
            return self._device.freezer_temperature
        elif self._sensor_type == "ambient":
            return self._device.ambient_temperature
        return None
