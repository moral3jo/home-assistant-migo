"""Climate entity for Saunier Duval MiGo."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MiGoAPIError, MiGoAuthError
from .const import (
    CONF_HOME_ID,
    CONF_HOME_NAME,
    DOMAIN,
    THERM_MODE_AWAY,
    THERM_MODE_FROST_GUARD,
    THERM_MODE_SCHEDULE,
)
from .coordinator import MiGoCoordinator

_LOGGER = logging.getLogger(__name__)

# Map Netatmo thermostat modes → HA HVAC modes
#   schedule  → AUTO  (at home, following programmed schedule)
#   away      → OFF   (ausente — caldera en modo ahorro)
#   hg        → OFF   (anti-hielo, same HA mode, detected via attribute)
_NETATMO_TO_HVAC: dict[str, HVACMode] = {
    THERM_MODE_SCHEDULE: HVACMode.AUTO,
    THERM_MODE_AWAY: HVACMode.OFF,
    THERM_MODE_FROST_GUARD: HVACMode.OFF,
    "manual": HVACMode.HEAT,
}

_HVAC_TO_NETATMO: dict[HVACMode, str] = {
    HVACMode.AUTO: THERM_MODE_SCHEDULE,
    HVACMode.OFF: THERM_MODE_AWAY,
    HVACMode.HEAT: THERM_MODE_SCHEDULE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MiGoCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MiGoClimate(coordinator, config_entry)])


class MiGoClimate(CoordinatorEntity[MiGoCoordinator], ClimateEntity):
    """Climate entity representing the whole MiGo home."""

    _attr_has_entity_name = True
    _attr_name = None  # Use device name as entity name
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

    def __init__(self, coordinator: MiGoCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        home_id = entry.data[CONF_HOME_ID]
        home_name = entry.data.get(CONF_HOME_NAME, "MiGo")

        self._attr_unique_id = f"migo_{home_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, home_id)},
            name=home_name,
            manufacturer="Saunier Duval",
            model="MiGo (Netatmo Energy)",
        )

    # ------------------------------------------------------------------
    # State properties — read from coordinator data
    # ------------------------------------------------------------------

    @property
    def hvac_mode(self) -> HVACMode | None:
        if not self.coordinator.data:
            return None
        mode = self.coordinator.data.get("therm_mode")
        return _NETATMO_TO_HVAC.get(mode, HVACMode.AUTO)

    @property
    def current_temperature(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("target_temperature")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return {
            "boiler_firing": self.coordinator.data.get("boiler_status", False),
            "therm_mode": self.coordinator.data.get("therm_mode"),
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Switch between schedule (AUTO/HEAT) and away (OFF)."""
        netatmo_mode = _HVAC_TO_NETATMO.get(hvac_mode, THERM_MODE_SCHEDULE)
        await self._set_mode(netatmo_mode)

    async def async_turn_on(self) -> None:
        """Switch to 'at home / schedule' mode."""
        await self._set_mode(THERM_MODE_SCHEDULE)

    async def async_turn_off(self) -> None:
        """Switch to 'away' mode."""
        await self._set_mode(THERM_MODE_AWAY)

    async def _set_mode(self, mode: str) -> None:
        try:
            await self.coordinator.api.set_therm_mode(
                self.coordinator.home_id, mode
            )
        except (MiGoAuthError, MiGoAPIError) as err:
            raise HomeAssistantError(f"MiGo: failed to set mode '{mode}': {err}") from err

        # Optimistic update — don't wait the full hour for the state to reflect
        if self.coordinator.data:
            self.coordinator.data["therm_mode"] = mode
            self.async_write_ha_state()

        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
