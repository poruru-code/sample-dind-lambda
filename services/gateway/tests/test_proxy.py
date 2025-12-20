import pytest
from unittest.mock import AsyncMock, patch
import httpx
from services.gateway.core.proxy import proxy_to_lambda


@pytest.mark.asyncio
async def test_proxy_to_lambda_uses_shared_client():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = httpx.Response(200, json={"message": "ok"})
    mock_client.post.return_value = mock_response

    target_container = "test-container"
    event = {"key": "value"}

    # We mock resolve_container_ip using patch, assuming it is imported in proxy.py
    with patch("services.gateway.core.proxy.resolve_container_ip") as mock_resolve:
        mock_resolve.return_value = "1.2.3.4"

        # Call with client injected
        try:
            response = await proxy_to_lambda(target_container, event, client=mock_client)
        except TypeError:
            pytest.fail("proxy_to_lambda does not accept 'client' argument")

        assert response == mock_response
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert "http://1.2.3.4:8080" in args[0]
