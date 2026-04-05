"""DataUpdateCoordinator for Saunier Duval MiGo."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MiGoAPI, MiGoAuthError, MiGoAPIError
from .const import CONF_HOME_ID, DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


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

        return _parse_home_status(home)


def _parse_home_status(home: dict) -> dict:
    """Extract the fields we care about from the raw homestatus payload."""
    rooms = {r["id"]: r for r in home.get("rooms", [])}
    modules = {m["id"]: m for m in home.get("modules", [])}

    # Use the first room's temperatures as the "home" temperature
    current_temperature: float | None = None
    target_temperature: float | None = None
    therm_mode: str | None = None

    for room in rooms.values():
        current_temperature = room.get("therm_measured_temperature")
        target_temperature = room.get("therm_setpoint_temperature")
        therm_mode = room.get("therm_setpoint_mode")
        break  # Only first room for now

    # Find the relay/thermostat module to get boiler firing status
    boiler_status: bool = False
    for module in modules.values():
        if module.get("type") in ("NATherm1", "NRV", "NAPlug"):
            boiler_status = bool(module.get("boiler_status", False))
            break

    return {
        "therm_mode": therm_mode,
        "current_temperature": current_temperature,
        "target_temperature": target_temperature,
        "boiler_status": boiler_status,
        "rooms": rooms,
        "modules": modules,
    }
