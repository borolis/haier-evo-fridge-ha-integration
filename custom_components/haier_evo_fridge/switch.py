"""Support for Haier Evo Fridge switches."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up Haier Evo Fridge switch platform."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        HaierFridgeVacationMode(device),
        HaierFridgeSuperCoolMode(device),
    ]

    async_add_entities(entities)


class HaierFridgeVacationMode(HaierFridgeEntity, SwitchEntity):
    """Haier Evo Fridge vacation mode switch."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device) -> None:
        """Initialize the switch."""
        super().__init__(device)
        self._attr_name = "Vacation Mode"
        self._attr_unique_id = f"{self._device.unique_id}_vacation_mode"

    @property
    def is_on(self) -> bool | None:
        """Return true if vacation mode is on."""
        return self._device.vacation_mode

    async def async_turn_on(self, **kwargs) -> None:
        """Turn vacation mode on."""
        await self._device.async_set_vacation_mode(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn vacation mode off."""
        await self._device.async_set_vacation_mode(False)


class HaierFridgeSuperCoolMode(HaierFridgeEntity, SwitchEntity):
    """Haier Evo Fridge super cool mode switch."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device) -> None:
        """Initialize the switch."""
        super().__init__(device)
        self._attr_name = "Super Cool Mode"
        self._attr_unique_id = f"{self._device.unique_id}_super_cool_mode"

    @property
    def is_on(self) -> bool | None:
        """Return true if super cool mode is on."""
        return self._device.super_cool_mode

    async def async_turn_on(self, **kwargs) -> None:
        """Turn super cool mode on."""
        await self._device.async_set_super_cool_mode(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn super cool mode off."""
        await self._device.async_set_super_cool_mode(False)
