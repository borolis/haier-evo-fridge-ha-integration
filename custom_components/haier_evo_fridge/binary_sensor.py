"""Support for Haier Evo Fridge door sensors."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up Haier Evo Fridge binary sensor platform."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        HaierFridgeDoorSensor(device),
    ]

    async_add_entities(entities)


class HaierFridgeDoorSensor(HaierFridgeEntity, BinarySensorEntity):
    """Haier Evo Fridge door sensor."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self._attr_name = "Door"
        self._attr_unique_id = f"{self._device.unique_id}_door"

    @property
    def is_on(self) -> bool | None:
        """Return true if door is open."""
        return self._device.door_open
