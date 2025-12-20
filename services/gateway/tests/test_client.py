import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx
from services.gateway.client import ManagerClient


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.mark.asyncio
async def test_ensure_container_success(mock_client):
    # Create a proper mock response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"host": "10.0.0.1"}
    mock_response.raise_for_status = MagicMock()  # No-op

    mock_client.post.return_value = mock_response

    manager_client = ManagerClient(mock_client)
    host = await manager_client.ensure_container("test-func", "test-image")

    assert host == "10.0.0.1"
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0].endswith("/containers/ensure")
    assert kwargs["json"]["function_name"] == "test-func"


@pytest.mark.asyncio
async def test_ensure_container_failure(mock_client):
    mock_client.post.side_effect = httpx.RequestError("Connection failed", request=MagicMock())

    manager_client = ManagerClient(mock_client)

    with pytest.raises(httpx.RequestError):
        await manager_client.ensure_container("test-func")
