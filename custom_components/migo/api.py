"""API client for Saunier Duval MiGo (Netatmo Energy white-label)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import asyncio

import aiohttp

from .const import (
    BASE_URL,
    MIGO_CLIENT_ID,
    MIGO_CLIENT_SECRET,
    MIGO_USER_AGENT,
    MIGO_USER_PREFIX,
)

_LOGGER = logging.getLogger(__name__)


class MiGoAuthError(Exception):
    """Authentication error — invalid credentials or expired refresh token."""


class MiGoAPIError(Exception):
    """Generic API communication error."""


class MiGoAPI:
    """Async client for the MiGo/Netatmo Energy API."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: float | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        # Unix timestamp when the access token expires
        self._token_expires_at: float | None = token_expires_at

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Obtain a fresh access token using username + password."""
        data = {
            "grant_type": "password",
            "client_id": MIGO_CLIENT_ID,
            "client_secret": MIGO_CLIENT_SECRET,
            "username": self._username,
            "password": self._password,
            "user_prefix": MIGO_USER_PREFIX,
            "scope": "read_thermostat write_thermostat",
        }
        await self._do_token_request(data)

    async def _refresh_access_token(self) -> None:
        """Use the refresh token to get a new access token."""
        if not self._refresh_token:
            await self.authenticate()
            return

        data = {
            "grant_type": "refresh_token",
            "client_id": MIGO_CLIENT_ID,
            "client_secret": MIGO_CLIENT_SECRET,
            "refresh_token": self._refresh_token,
        }
        try:
            await self._do_token_request(data)
        except MiGoAuthError:
            _LOGGER.warning("Refresh token expired, re-authenticating with password")
            await self.authenticate()

    async def _do_token_request(self, data: dict) -> None:
        headers = {"User-Agent": MIGO_USER_AGENT}
        try:
            async with self._session.post(
                f"{BASE_URL}/oauth2/token",
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (400, 401, 403):
                    body = await resp.text()
                    _LOGGER.debug("Auth error response: %s", body)
                    raise MiGoAuthError(f"Authentication failed (HTTP {resp.status})")
                resp.raise_for_status()
                result = await resp.json()
        except MiGoAuthError:
            raise
        except aiohttp.ClientError as err:
            raise MiGoAPIError(f"Network error during auth: {err}") from err

        self._access_token = result["access_token"]
        self._refresh_token = result.get("refresh_token", self._refresh_token)
        expires_in = result.get("expires_in", 10800)
        # Subtract 60 s buffer so we refresh slightly before actual expiry
        self._token_expires_at = (
            datetime.now() + timedelta(seconds=expires_in - 60)
        ).timestamp()
        _LOGGER.debug("Token obtained/refreshed, expires in %s s", expires_in)

    async def _ensure_token(self) -> None:
        if self._access_token is None:
            await self.authenticate()
        elif (
            self._token_expires_at is not None
            and datetime.now().timestamp() >= self._token_expires_at
        ):
            await self._refresh_access_token()

    def get_token_info(self) -> dict:
        """Return current token data to persist in the config entry."""
        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "token_expires_at": self._token_expires_at,
        }

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict | None = None) -> dict:
        await self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": MIGO_USER_AGENT,
        }
        try:
            async with self._session.get(
                f"{BASE_URL}{path}",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (401, 403):
                    raise MiGoAuthError(f"Auth error on GET {path}")
                resp.raise_for_status()
                return await resp.json()
        except MiGoAuthError:
            raise
        except aiohttp.ClientError as err:
            raise MiGoAPIError(f"GET {path} failed: {err}") from err

    async def _post(self, path: str, payload: dict) -> dict:
        await self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": MIGO_USER_AGENT,
        }
        try:
            async with self._session.post(
                f"{BASE_URL}{path}",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (401, 403):
                    raise MiGoAuthError(f"Auth error on POST {path}")
                resp.raise_for_status()
                return await resp.json()
        except MiGoAuthError:
            raise
        except aiohttp.ClientError as err:
            raise MiGoAPIError(f"POST {path} failed: {err}") from err

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    async def get_homes_data(self) -> dict:
        """Return static topology: homes, rooms, modules."""
        return await self._get("/api/homesdata")

    async def get_home_status(self, home_id: str) -> dict:
        """Return real-time state for a specific home."""
        return await self._get("/api/homestatus", params={"home_id": home_id})

    async def get_homes_and_status(self, home_id: str) -> tuple[dict, dict]:
        """Fetch homesdata and homestatus in parallel.

        homesdata contains the home-level therm_mode (away/schedule/hg).
        homestatus contains real-time temperatures and boiler status.
        """
        await self._ensure_token()
        homes_data, status_data = await asyncio.gather(
            self.get_homes_data(),
            self.get_home_status(home_id),
        )
        return homes_data, status_data

    async def set_therm_mode(self, home_id: str, mode: str) -> dict:
        """Set the global thermostat mode for a home.

        mode: 'schedule' (at home), 'away' (ausente), 'hg' (frost guard)
        """
        return await self._post(
            "/api/setthermmode", {"home_id": home_id, "mode": mode}
        )
