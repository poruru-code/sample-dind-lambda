import pytest
from unittest.mock import Mock
from fastapi import Request, Response
from services.gateway.main import trace_propagation_middleware
from services.common.core.request_context import get_trace_id, clear_trace_id


@pytest.mark.asyncio
async def test_trace_propagation_middleware_sets_context():
    # Setup
    clear_trace_id()
    expected_tid = "Root=1-6789abcd-1234567890abcdef12345678;Sampled=1"

    # Mock Request
    mock_request = Mock(spec=Request)
    mock_request.headers = {"X-Amzn-Trace-Id": expected_tid}
    mock_request.method = "GET"
    mock_request.url.path = "/test"

    # Mock call_next
    async def mock_call_next(request):
        # Verify context INSIDE the next call
        current_tid = get_trace_id()
        assert current_tid == expected_tid, (
            f"Context TraceId inside call_next mismatch: {current_tid}"
        )
        return Response(status_code=200)

    # Execute
    response = await trace_propagation_middleware(mock_request, mock_call_next)

    # Verify Response Header
    assert response.headers["X-Amzn-Trace-Id"] == expected_tid


@pytest.mark.asyncio
async def test_trace_propagation_middleware_generates_id_if_missing():
    clear_trace_id()

    mock_request = Mock(spec=Request)
    mock_request.headers = {}  # No X-Amzn-Trace-Id
    mock_request.method = "GET"
    mock_request.url.path = "/test"

    captured_tid = None

    async def mock_call_next(request):
        nonlocal captured_tid
        captured_tid = get_trace_id()
        return Response(status_code=200)

    response = await trace_propagation_middleware(mock_request, mock_call_next)

    assert captured_tid is not None
    assert response.headers["X-Amzn-Trace-Id"] == captured_tid
    assert captured_tid.startswith("Root=1-")
