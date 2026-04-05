"""Button entity for Saunier Duval MiGo — manual data refresh."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_HOME_ID, CONF_HOME_NAME, DOMAIN
from .coordinator import MiGoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MiGoCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MiGoRefreshButton(coordinator, config_entry)])


class MiGoRefreshButton(ButtonEntity):
    """Button that forces an immediate poll of the MiGo API."""

    _attr_has_entity_name = True
    _attr_name = "Actualizar"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: MiGoCoordinator, entry: ConfigEntry) -> None:
        home_id = entry.data[CONF_HOME_ID]
        home_name = entry.data.get(CONF_HOME_NAME, "MiGo")

        self._coordinator = coordinator
        self._attr_unique_id = f"migo_{home_id}_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, home_id)},
            name=home_name,
            manufacturer="Saunier Duval",
            model="MiGo (Netatmo Energy)",
        )

    async def async_press(self) -> None:
        """Trigger an immediate data refresh."""
        await self._coordinator.async_request_refresh()
