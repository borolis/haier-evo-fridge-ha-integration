from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from .logger import _LOGGER
from .const import DOMAIN
from . import api


PLATFORMS: list[str] = ["binary_sensor", "number", "sensor", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.debug(f'Integration version: {integration.version}')
    haier_object = api.Haier(hass, entry.data["email"], entry.data["password"])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = haier_object
    await hass.async_add_executor_job(haier_object.load_tokens)
    await hass.async_add_executor_job(haier_object.pull_data)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
