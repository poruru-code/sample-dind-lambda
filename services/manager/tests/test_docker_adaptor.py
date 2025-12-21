import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.manager.docker_adaptor import DockerAdaptor


@pytest.mark.asyncio
async def test_prune_containers_method_exists():
    """
    TDD: DockerAdaptor should have an async prune_containers method.
    """
    adaptor = DockerAdaptor()
    assert hasattr(adaptor, "prune_containers")
    assert callable(getattr(adaptor, "prune_containers"))


@pytest.mark.asyncio
async def test_prune_containers_uses_executor():
    """
    TDD: prune_containers should use run_in_executor to avoid blocking event loop.
    """
    with patch("services.manager.docker_adaptor.docker.from_env") as mock_docker:
        mock_client = Mock()
        mock_docker.return_value = mock_client
        mock_client.containers.list.return_value = []

        adaptor = DockerAdaptor()

        # Mock the event loop to verify run_in_executor is called
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop_instance = AsyncMock()
            mock_loop.return_value = mock_loop_instance
            mock_loop_instance.run_in_executor = AsyncMock(return_value=None)

            await adaptor.prune_containers()

            # Verify run_in_executor was called
            mock_loop_instance.run_in_executor.assert_awaited_once()
