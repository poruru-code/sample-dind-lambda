from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os
import docker

# Add the project root to sys.path to allow imports from services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# We will implement this next
from services.manager.main import app, manager

client = TestClient(app)


def test_ensure_container_starts_new():
    """Verify that a new container is started if it doesn't exist."""
    # Build Docker Client Mock
    mock_client = MagicMock()

    # Inject mock client into the global manager instance, and mock socket to avoid wait
    # Also ensure manager uses the network name present in our mock data
    with (
        patch.object(manager, "client", mock_client),
        patch("services.manager.service.socket.create_connection"),
        patch.object(manager, "network", "dind-network"),
    ):
        # Existing containers list is empty
        mock_client.containers.list.return_value = []
        # run return value
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {"Networks": {"dind-network": {"IPAddress": "10.0.0.5"}}}
        }
        mock_client.containers.run.return_value = mock_container

        # Execute API
        response = client.post("/containers/ensure", json={"function_name": "lambda-hello"})

        # Verify
        assert response.status_code == 200
        assert response.json()["host"] == "10.0.0.5"

        # Verify strict call arguments
        mock_client.containers.run.assert_called_once()
        args, kwargs = mock_client.containers.run.call_args
    # Image might be positional or kwarg
    actual_image = kwargs.get("image")
    if not actual_image and args:
        actual_image = args[0]

    assert actual_image == "lambda-hello:latest"
    assert kwargs.get("privileged", False) is False


def test_ensure_container_image_not_found():
    """Verify that 404 is returned if the image is not found."""
    import docker.errors

    mock_client = MagicMock()
    # Mocking containers.get to raise NotFound, and run to raise ImageNotFound
    mock_client.containers.get.side_effect = docker.errors.NotFound("Not found")
    mock_client.containers.run.side_effect = docker.errors.ImageNotFound(
        "No such image", response=MagicMock()
    )

    with (
        patch.object(manager, "client", mock_client),
        patch.object(manager, "network", "dind-network"),
    ):
        response = client.post("/containers/ensure", json={"function_name": "unknown-func"})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_ensure_container_concurrency():
    """Verify that multiple concurrent requests result in only one creation."""
    from concurrent.futures import ThreadPoolExecutor

    mock_client = MagicMock()
    mock_client.containers.list.return_value = []

    # Slow start simulation
    def slow_run(*args, **kwargs):
        import time

        time.sleep(0.5)
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {"Networks": {"dind-network": {"IPAddress": "10.0.0.5"}}}
        }
        return mock_container

    mock_client.containers.run.side_effect = slow_run
    # Mocking get to return NotFound initially, then success for subsequent calls
    mock_running_container = MagicMock()
    mock_running_container.status = "running"
    mock_running_container.attrs = {
        "NetworkSettings": {"Networks": {"dind-network": {"IPAddress": "10.0.0.5"}}}
    }

    mock_client.containers.get.side_effect = [
        docker.errors.NotFound("Not found"),
        mock_running_container,
        mock_running_container,
        mock_running_container,
        mock_running_container,
        mock_running_container,
    ]

    with (
        patch.object(manager, "client", mock_client),
        patch("services.manager.service.socket.create_connection"),
        patch.object(manager, "network", "dind-network"),
    ):
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Send 5 requests simultaneously
            futures = [
                executor.submit(
                    client.post, "/containers/ensure", json={"function_name": "busy-func"}
                )
                for _ in range(5)
            ]
            responses = [f.result() for f in futures]

        # All should succeed
        for resp in responses:
            assert resp.status_code == 200

        # Run should be called ONLY ONCE despite 5 requests
        assert mock_client.containers.run.call_count == 1


def test_ensure_container_ip_fallback():
    """Verify that it falls back to container name if IP address is missing."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.status = "running"
    # Network or IPAddress is missing
    mock_container.attrs = {"NetworkSettings": {"Networks": {}}}
    mock_client.containers.get.return_value = mock_container

    with (
        patch.object(manager, "client", mock_client),
        patch("services.manager.service.socket.create_connection"),
        patch.object(manager, "network", "dind-network"),
    ):
        response = client.post("/containers/ensure", json={"function_name": "fallback-func"})

        assert response.status_code == 200
        # Host should be container name if IP not found
        assert response.json()["host"] == "fallback-func"


def test_ensure_container_readiness_with_ip():
    """Verify that readiness check is performed using the IP address."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {
        "NetworkSettings": {"Networks": {"dind-network": {"IPAddress": "10.0.0.99"}}}
    }
    mock_client.containers.get.return_value = mock_container

    with (
        patch.object(manager, "client", mock_client),
        patch("services.manager.service.socket.create_connection") as mock_conn,
        patch.object(manager, "network", "dind-network"),
    ):
        response = client.post("/containers/ensure", json={"function_name": "ip-check-func"})

        assert response.status_code == 200
        assert response.json()["host"] == "10.0.0.99"

        # Verify create_connection was called with IP ADDRESS, not function name
        # args[0] is (address, port)
        args, _ = mock_conn.call_args
        target_addr = args[0][0]
        assert target_addr == "10.0.0.99"
        assert target_addr != "ip-check-func"
