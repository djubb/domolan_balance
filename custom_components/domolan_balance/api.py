"""Minimal API client for the domolan.ru subscriber cabinet.

domolan.ru is a Sails.js application. It protects mutating/`/api/*` calls
with a CSRF token that must first be fetched from ``GET /csrf-token`` and
then echoed back as the ``X-Csrf-Token`` header on every ``/api/*``
request. The session itself lives in the ``sails.sid`` cookie set by that
same call (and refreshed on login).

Reverse-engineered from the site's own public JS bundle (Vite build), see
the integration README for details. There is no official/public API.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import BASE_URL, CSRF_TOKEN_PATH, LOGIN_PATH, USER_DATA_PATH

_LOGGER = logging.getLogger(__name__)


class DomolanApiError(Exception):
    """Generic error talking to domolan.ru."""


class DomolanAuthError(DomolanApiError):
    """Raised when login fails or the session is no longer valid."""


class DomolanApiClient:
    """Handles CSRF, login and balance retrieval for one account."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        login: str,
        password: str,
    ) -> None:
        self._session = session
        self._login = login
        self._password = password
        self._csrf_token: str | None = None

    async def _fetch_csrf_token(self) -> str:
        """Fetch (or refresh) the CSRF token, also seeding the session cookie."""
        try:
            async with self._session.get(
                f"{BASE_URL}{CSRF_TOKEN_PATH}"
            ) as resp:
                if resp.status != 200:
                    raise DomolanApiError(
                        f"Unexpected status {resp.status} fetching CSRF token"
                    )
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise DomolanApiError(f"Network error fetching CSRF token: {err}") from err

        token = data.get("_csrf") if isinstance(data, dict) else None
        if not token:
            raise DomolanApiError("CSRF token missing from response")
        self._csrf_token = token
        return token

    async def _api_request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        retry_on_csrf_failure: bool = True,
    ) -> aiohttp.ClientResponse:
        """Perform a request under /api/, attaching the CSRF header.

        On a 403 (stale/missing CSRF token) the token is refreshed once and
        the request retried, mirroring the site's own axios interceptor.
        """
        if self._csrf_token is None:
            await self._fetch_csrf_token()

        headers = {"X-Csrf-Token": self._csrf_token or ""}
        try:
            resp = await self._session.request(
                method, f"{BASE_URL}{path}", json=json, headers=headers
            )
        except aiohttp.ClientError as err:
            raise DomolanApiError(f"Network error calling {path}: {err}") from err

        if resp.status == 403 and retry_on_csrf_failure:
            resp.close()
            await self._fetch_csrf_token()
            return await self._api_request(
                method, path, json=json, retry_on_csrf_failure=False
            )

        return resp

    async def async_login(self) -> int:
        """Log in and return the numeric user id. Raises DomolanAuthError on bad creds."""
        resp = await self._api_request(
            "POST",
            LOGIN_PATH,
            json={"login": self._login, "password": self._password},
        )
        async with resp:
            if resp.status == 400:
                raise DomolanAuthError("Invalid login or password")
            if resp.status != 200:
                text = await resp.text()
                raise DomolanApiError(
                    f"Unexpected status {resp.status} logging in: {text[:200]}"
                )
            body = (await resp.text()).strip()

        try:
            return int(body)
        except ValueError as err:
            raise DomolanApiError(f"Unexpected login response: {body[:200]}") from err

    async def async_get_user_data(self) -> dict[str, Any]:
        """Fetch the account dashboard payload (includes ``balance``)."""
        resp = await self._api_request("GET", USER_DATA_PATH)
        async with resp:
            if resp.status == 401:
                raise DomolanAuthError("Session expired or not logged in")
            if resp.status != 200:
                text = await resp.text()
                raise DomolanApiError(
                    f"Unexpected status {resp.status} fetching user data: {text[:200]}"
                )
            return await resp.json(content_type=None)

    async def async_ensure_logged_in_and_get_balance(self) -> dict[str, Any]:
        """Fetch user data, logging in first (or again) if the session is invalid."""
        try:
            return await self.async_get_user_data()
        except DomolanAuthError:
            _LOGGER.debug("Session invalid/expired, logging in again")
            await self.async_login()
            return await self.async_get_user_data()
