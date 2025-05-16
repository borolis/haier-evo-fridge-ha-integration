"""Support for Haier Evo Fridge temperature control."""
from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HaierFridgeEntity
from .const import (
    DOMAIN,
    MIN_FRIDGE_TEMP,
    MAX_FRIDGE_TEMP,
    MIN_FREEZER_TEMP,
    MAX_FREEZER_TEMP,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Haier Evo Fridge number platform."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        HaierFridgeTemperatureControl(device, "fridge", "Fridge Temperature Control"),
        HaierFridgeTemperatureControl(device, "freezer", "Freezer Temperature Control"),
    ]

    async_add_entities(entities)


class HaierFridgeTemperatureControl(HaierFridgeEntity, NumberEntity):
    """Haier Evo Fridge temperature control."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER

    def __init__(self, device, control_type, name) -> None:
        """Initialize the control."""
        super().__init__(device)
        self._control_type = control_type
        self._attr_name = f"{name}"
        self._attr_unique_id = f"{self._device.unique_id}_{control_type}_temperature_control"

        if control_type == "fridge":
            self._attr_native_min_value = MIN_FRIDGE_TEMP
            self._attr_native_max_value = MAX_FRIDGE_TEMP
            self._attr_native_step = 1.0
        else:  # freezer
            self._attr_native_min_value = MIN_FREEZER_TEMP
            self._attr_native_max_value = MAX_FREEZER_TEMP
            self._attr_native_step = 1.0

    @property
    def native_value(self) -> float | None:
        """Return the current temperature setting."""
        if self._control_type == "fridge":
            return self._device.fridge_target_temperature
        return self._device.freezer_target_temperature

    async def async_set_native_value(self, value: float) -> None:
        """Set new target temperature."""
        if self._control_type == "fridge":
            await self._device.async_set_fridge_temperature(int(value))
        else:
            await self._device.async_set_freezer_temperature(int(value))
