from __future__ import annotations

import asyncio
import csv
import io
from urllib.parse import urlparse

from .errors import ApiError, ConfigurationError
from .models import Profile

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None


class RedcapClient:
    def __init__(self, profile: Profile, token: str, client: object | None = None):
        parsed = urlparse(profile.api_url)
        if parsed.scheme not in {"https", "http"} or (
            parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ConfigurationError(
                "API URL must use HTTPS (HTTP is allowed only for localhost testing)."
            )
        self.profile, self.token, self._client = profile, token, client

    async def export(self, content: str, **payload: object) -> list[dict[str, str]]:
        payload = {
            "token": self.token,
            "content": content,
            "format": "csv",
            "returnFormat": "csv",
            **payload,
        }
        text = await self._post(payload)
        try:
            return list(csv.DictReader(io.StringIO(text)))
        except csv.Error as exc:
            raise ApiError("REDCap returned malformed CSV.") from exc

    async def project_info(self) -> dict[str, str]:
        rows = await self.export("project")
        return rows[0] if rows else {}

    async def _post(self, data: dict[str, object]) -> str:
        if self._client is not None:
            response = await self._client.post(
                self.profile.api_url, data=data, follow_redirects=False
            )
            return self._response_text(response)
        if httpx is None:
            raise ConfigurationError("The httpx dependency is not installed.")
        verify: object = self.profile.ca_bundle or True
        async with httpx.AsyncClient(verify=verify, timeout=30, follow_redirects=False) as client:
            for attempt in range(3):
                try:
                    response = await client.post(self.profile.api_url, data=data)
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    return self._response_text(response)
                except httpx.TimeoutException as exc:
                    if attempt == 2:
                        raise ApiError("REDCap request timed out.") from exc
                    await asyncio.sleep(0.5 * (2**attempt))
                except httpx.HTTPError as exc:
                    raise ApiError("Could not securely reach the REDCap API.") from exc
        raise ApiError("REDCap request failed.")

    @staticmethod
    def _response_text(response: object) -> str:
        status = response.status_code
        if 300 <= status < 400:
            raise ApiError("REDCap returned a redirect, which was rejected for safety.")
        if status >= 400:
            raise ApiError("REDCap rejected the request; check API access and permissions.")
        text = response.text
        if text.lstrip().startswith("{") and "error" in text.lower():
            raise ApiError(
                "REDCap returned an API error; check the requested fields and permissions."
            )
        return text
