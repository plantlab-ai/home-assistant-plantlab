import asyncio

import aiohttp

from .const import USER_AGENT


class PlantLabAuthError(Exception):
    pass


class PlantLabConnectionError(Exception):
    pass


class PlantLabRateLimitError(Exception):
    pass


def _wait_text(seconds: int | None) -> str:
    if seconds is None:
        return "Try again later."
    minutes = max(1, -(-seconds // 60))
    if minutes == 1:
        return "Try again in about 1 minute."
    if minutes < 120:
        return f"Try again in about {minutes} minutes."
    return f"Try again in about {-(-minutes // 60)} hours."


async def _rate_limit_error(resp: aiohttp.ClientResponse) -> PlantLabRateLimitError:
    """Build the error for a 429 from the API's `code`, `limit` and `retryAfter`."""
    try:
        body = await resp.json(content_type=None)
    except (aiohttp.ContentTypeError, ValueError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    code = body.get("code")
    limit = body.get("limit")
    retry_after = body.get("retryAfter")
    if not isinstance(retry_after, int):
        header = resp.headers.get("Retry-After", "")
        retry_after = int(header) if header.isdigit() else None
    wait = _wait_text(retry_after)
    if code == "DAILY_LIMIT_EXCEEDED":
        return PlantLabRateLimitError(f"Daily limit of {limit} diagnoses reached. {wait}")
    if code == "MONTHLY_LIMIT_EXCEEDED":
        return PlantLabRateLimitError(f"Monthly limit of {limit} diagnoses reached. {wait}")
    return PlantLabRateLimitError(f"Too many requests. {wait}")


class PlantLabTierError(Exception):
    """Raised when the API returns 403 (free tier or opt-in disabled)."""


class PlantLabApiClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        host: str,
        timeout: int = 30,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._host = host.rstrip("/")
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key, "User-Agent": USER_AGENT}

    async def async_validate(self) -> bool:
        try:
            async with asyncio.timeout(10):
                resp = await self._session.get(
                    f"{self._host}/info",
                    headers=self._headers,
                )
                if resp.status == 401:
                    raise PlantLabAuthError("Invalid API key")
                resp.raise_for_status()
                return True
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PlantLabConnectionError(f"Unable to connect to PlantLab API at {self._host}") from err

    async def async_diagnose(self, image_bytes: bytes, filename: str = "snapshot.jpg") -> dict:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        content_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        content_type = content_types.get(ext, "image/jpeg")

        data = aiohttp.FormData()
        data.add_field(
            "image",
            image_bytes,
            filename=filename,
            content_type=content_type,
        )
        try:
            async with asyncio.timeout(self._timeout):
                resp = await self._session.post(
                    f"{self._host}/diagnose",
                    data=data,
                    headers=self._headers,
                )
                if resp.status == 401:
                    raise PlantLabAuthError("Invalid API key")
                if resp.status == 429:
                    raise await _rate_limit_error(resp)
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PlantLabConnectionError(f"Error communicating with PlantLab API: {err}") from err

    async def async_get_history(self, since_iso: str, limit: int = 1000) -> dict:
        """Fetch diagnosis history records.

        Returns the parsed JSON body on success.
        Raises PlantLabTierError on 403 (free tier or opt-in disabled).
        Raises PlantLabConnectionError on network/timeout errors.
        """
        params = {"since": since_iso, "limit": str(limit)}
        try:
            async with asyncio.timeout(5):
                resp = await self._session.get(
                    f"{self._host}/history",
                    headers=self._headers,
                    params=params,
                )
                if resp.status == 403:
                    raise PlantLabTierError("History not available: free tier or training opt-in disabled")
                if resp.status == 401:
                    raise PlantLabAuthError("Invalid API key")
                resp.raise_for_status()
                return await resp.json()
        except PlantLabTierError:
            raise
        except PlantLabAuthError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PlantLabConnectionError(f"Error fetching history from PlantLab API: {err}") from err
