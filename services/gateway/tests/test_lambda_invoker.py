import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

# Assuming the class will be created in this module
from services.gateway.services.lambda_invoker import LambdaInvoker


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post.return_value = httpx.Response(200, json={"message": "ok"})
    return client


@pytest.fixture
def mock_registry():
    registry = Mock()
    registry.get_function_config.return_value = {"image": "test-image", "environment": {}}
    return registry


@pytest.mark.asyncio
async def test_invoke_function(mock_client, mock_registry):
    # Patching get_lambda_host where it is imported in lambda_invoker.py
    with patch(
        "services.gateway.services.lambda_invoker.get_lambda_host", new_callable=AsyncMock
    ) as mock_get_host:
        mock_get_host.return_value = "1.2.3.4"

        invoker = LambdaInvoker(mock_client, mock_registry)
        response = await invoker.invoke_function("test-func", b"{}")

        assert response.status_code == 200
        mock_client.post.assert_called_once()
        # Verify URL construction
        args, kwargs = mock_client.post.call_args
        assert "http://1.2.3.4:8080" in args[0]
