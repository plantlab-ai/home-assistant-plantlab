from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.plantlab.api import (
    PlantLabApiClient,
    PlantLabAuthError,
    PlantLabConnectionError,
    PlantLabRateLimitError,
)

from .conftest import DIAGNOSE_RESPONSE_HEALTHY, MOCK_API_KEY, MOCK_HOST


@pytest.fixture
def mock_session():
    return MagicMock(spec=aiohttp.ClientSession)


def _make_response(status: int, json_data: dict | None = None):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=status,
        )
    return resp


async def test_validate_success(mock_session):
    mock_session.get = AsyncMock(return_value=_make_response(200, {"version": "1.0.0"}))
    client = PlantLabApiClient(mock_session, MOCK_API_KEY, MOCK_HOST)
    result = await client.async_validate()
    assert result is True
    mock_session.get.assert_called_once()
    call_kwargs = mock_session.get.call_args
    assert call_kwargs[1]["headers"]["X-API-Key"] == MOCK_API_KEY


async def test_validate_invalid_key(mock_session):
    mock_session.get = AsyncMock(return_value=_make_response(401))
    client = PlantLabApiClient(mock_session, "bad_key", MOCK_HOST)
    with pytest.raises(PlantLabAuthError):
        await client.async_validate()


async def test_validate_connection_error(mock_session):
    mock_session.get = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
    client = PlantLabApiClient(mock_session, MOCK_API_KEY, MOCK_HOST)
    with pytest.raises(PlantLabConnectionError):
        await client.async_validate()


async def test_diagnose_success(mock_session):
    mock_session.post = AsyncMock(return_value=_make_response(200, DIAGNOSE_RESPONSE_HEALTHY))
    client = PlantLabApiClient(mock_session, MOCK_API_KEY, MOCK_HOST)
    result = await client.async_diagnose(b"fake_image_bytes", "test.jpg")
    assert result["success"] is True
    assert result["is_cannabis"] is True


async def test_diagnose_auth_error(mock_session):
    mock_session.post = AsyncMock(return_value=_make_response(401))
    client = PlantLabApiClient(mock_session, "bad_key", MOCK_HOST)
    with pytest.raises(PlantLabAuthError):
        await client.async_diagnose(b"fake_image_bytes")


async def test_diagnose_rate_limit(mock_session):
    mock_session.post = AsyncMock(return_value=_make_response(429))
    client = PlantLabApiClient(mock_session, MOCK_API_KEY, MOCK_HOST)
    with pytest.raises(PlantLabRateLimitError, match="free tier"):
        await client.async_diagnose(b"fake_image_bytes")


async def test_diagnose_server_error(mock_session):
    mock_session.post = AsyncMock(return_value=_make_response(500))
    client = PlantLabApiClient(mock_session, MOCK_API_KEY, MOCK_HOST)
    with pytest.raises(PlantLabConnectionError):
        await client.async_diagnose(b"fake_image_bytes")


async def test_diagnose_timeout(mock_session):
    mock_session.post = AsyncMock(side_effect=TimeoutError)
    client = PlantLabApiClient(mock_session, MOCK_API_KEY, MOCK_HOST, timeout=1)
    with pytest.raises(PlantLabConnectionError):
        await client.async_diagnose(b"fake_image_bytes")


async def test_host_trailing_slash_stripped(mock_session):
    mock_session.get = AsyncMock(return_value=_make_response(200, {}))
    client = PlantLabApiClient(mock_session, MOCK_API_KEY, "https://api.plantlab.ai/")
    await client.async_validate()
    url = mock_session.get.call_args[0][0]
    assert not url.startswith("https://api.plantlab.ai//")
