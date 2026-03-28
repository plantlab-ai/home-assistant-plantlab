import asyncio

import aiohttp


class PlantLabAuthError(Exception):
    pass


class PlantLabConnectionError(Exception):
    pass


class PlantLabRateLimitError(Exception):
    pass


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
        return {"X-API-Key": self._api_key}

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
                    raise PlantLabRateLimitError("Rate limit exceeded - free tier allows 3 diagnoses/day")
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PlantLabConnectionError(f"Error communicating with PlantLab API: {err}") from err
