"""DataUpdateCoordinator for Saunier Duval MiGo."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MiGoAPI, MiGoAuthError, MiGoAPIError
from .const import CONF_HOME_ID, DOMAIN, SCAN_INTERVAL_SECONDS, THERM_MODE_SCHEDULE

_LOGGER = logging.getLogger(__name__)

# Module types that carry boiler_status in this white-label firmware
_BOILER_MODULE_TYPES = {"NATherm1", "NRV", "NAPlug", "NAThermVaillant", "NAVaillant"}


class MiGoCoordinator(DataUpdateCoordinator):
    """Coordinator that polls MiGo once per hour to avoid rate-limit bans."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: MiGoAPI,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.api = api
        self.home_id: str = config_entry.data[CONF_HOME_ID]
        # The homestatus API does not return the home-level thermostat mode.
        # We track it locally and update it whenever setthermmode is called.
        self._tracked_mode: str = THERM_MODE_SCHEDULE

    def set_tracked_mode(self, mode: str) -> None:
        """Store the mode we just sent to the API so polls don't overwrite it."""
        self._tracked_mode = mode

    async def _async_update_data(self) -> dict:
        """Fetch current home status from the API."""
        try:
            data = await self.api.get_home_status(self.home_id)
        except MiGoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MiGoAPIError as err:
            raise UpdateFailed(f"Error communicating with MiGo API: {err}") from err

        home = data.get("body", {}).get("home", {})
        if not home:
            raise UpdateFailed("Unexpected API response: 'home' key missing")

        # Persist potentially refreshed tokens back into the config entry
        token_info = self.api.get_token_info()
        if token_info.get("access_token") != self.config_entry.data.get("access_token"):
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, **token_info},
            )

        parsed = _parse_home_status(home)
        # Inject the locally-tracked mode — the API always returns "home" at
        # room level regardless of the home-level mode set via setthermmode.
        parsed["therm_mode"] = self._tracked_mode
        return parsed


def _parse_home_status(home: dict) -> dict:
    """Extract the fields we care about from the raw homestatus payload."""
    rooms = {r["id"]: r for r in home.get("rooms", [])}
    modules = {m["id"]: m for m in home.get("modules", [])}

    # Use the first room's temperatures as the "home" temperature
    current_temperature: float | None = None
    target_temperature: float | None = None

    for room in rooms.values():
        current_temperature = room.get("therm_measured_temperature")
        target_temperature = room.get("therm_setpoint_temperature")
        break  # Only first room for now

    # Find the thermostat module for boiler firing status and outdoor temperature
    boiler_status: bool = False
    outdoor_temperature: float | None = None

    for module in modules.values():
        mod_type = module.get("type", "")
        if mod_type in _BOILER_MODULE_TYPES:
            if "boiler_status" in module:
                boiler_status = bool(module["boiler_status"])
        if "outdoor_temperature" in module:
            outdoor_temperature = module["outdoor_temperature"]

    return {
        "therm_mode": None,  # filled in by coordinator after injection
        "current_temperature": current_temperature,
        "target_temperature": target_temperature,
        "boiler_status": boiler_status,
        "outdoor_temperature": outdoor_temperature,
        "rooms": rooms,
        "modules": modules,
    }
