import pytest
from unittest.mock import MagicMock, AsyncMock, Mock, patch
import docker.errors
from services.manager.service import ContainerManager


@pytest.fixture
def mock_docker_adaptor():
    # Patch the class in the service module
    with patch("services.manager.service.DockerAdaptor") as mock_cls:
        adaptor = Mock()  # The instance
        mock_cls.return_value = adaptor
        yield adaptor


@pytest.mark.asyncio
async def test_ensure_container_running_cold_start(mock_docker_adaptor):
    # Mock methods of adaptor to be async
    mock_docker_adaptor.get_container = AsyncMock()
    mock_docker_adaptor.run_container = AsyncMock()
    mock_docker_adaptor.reload_container = AsyncMock()
    mock_docker_adaptor.remove_container = AsyncMock()

    manager = ContainerManager(network="test-net")

    # Mock get_container to raise NotFound
    mock_docker_adaptor.get_container.side_effect = docker.errors.NotFound("Not found")

    # Mock run_container
    mock_container = MagicMock()
    mock_container.attrs = {"NetworkSettings": {"Networks": {"test-net": {"IPAddress": "1.2.3.4"}}}}
    mock_docker_adaptor.run_container.return_value = mock_container

    # Mock internal readiness wait
    with patch.object(manager, "_wait_for_readiness", new_callable=AsyncMock) as mock_wait:
        result = await manager.ensure_container_running("test-func", "test-image")

        assert result == "test-func"
        mock_docker_adaptor.run_container.assert_awaited_once()
        mock_wait.assert_awaited_once_with("1.2.3.4")


@pytest.mark.asyncio
async def test_ensure_container_running_warm_start(mock_docker_adaptor):
    mock_docker_adaptor.get_container = AsyncMock()
    mock_docker_adaptor.run_container = AsyncMock()
    mock_docker_adaptor.reload_container = AsyncMock()

    manager = ContainerManager(network="test-net")

    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"NetworkSettings": {"Networks": {"test-net": {"IPAddress": "1.2.3.4"}}}}

    # Warm start: get returns running container
    mock_docker_adaptor.get_container.side_effect = None
    mock_docker_adaptor.get_container.return_value = mock_container

    with patch.object(manager, "_wait_for_readiness", new_callable=AsyncMock) as mock_wait:
        result = await manager.ensure_container_running("test-func")

        assert result == "test-func"
        mock_docker_adaptor.run_container.assert_not_awaited()
        mock_wait.assert_awaited_once_with("1.2.3.4")
