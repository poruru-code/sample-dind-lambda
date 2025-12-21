"""
Docker Client Adapter for Async IO

Blocking docker-py calls are offloaded to an executor.
"""

import asyncio
import docker
import logging
from typing import Any, List

logger = logging.getLogger("manager.docker_adaptor")


class DockerAdaptor:
    def __init__(self):
        self._client = docker.from_env()

    async def get_container(self, name: str) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._client.containers.get, name)

    async def run_container(self, image: str, **kwargs) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._client.containers.run(image, **kwargs)
        )

    async def list_containers(self, **kwargs) -> List[Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._client.containers.list(**kwargs))

    # Note: Accessing attributes of a container object (like container.status) is usually fast/cached
    # IF it was just returned by get/run.
    # BUT container.reload() is network I/O.

    async def reload_container(self, container: Any) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, container.reload)

    async def stop_container(self, container: Any) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, container.stop)

    async def remove_container(self, container: Any, force: bool = False) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: container.remove(force=force))

    async def kill_container(self, container: Any) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, container.kill)

    async def prune_containers(self) -> None:
        """
        ゾンビコンテナ（label=created_by=sample-dind）を削除します。

        非同期処理のため、run_in_executorを使用してブロッキングを回避します。
        """

        def _prune():
            """同期的なコンテナ削除処理"""
            try:
                containers = self._client.containers.list(
                    all=True,  # Include stopped ones
                    filters={"label": "created_by=sample-dind"},
                )
                for container in containers:
                    logger.info(f"Removing zombie container: {container.name}")
                    try:
                        if container.status == "running":
                            container.kill()
                        container.remove(force=True)
                    except Exception as e:
                        logger.error(f"Error removing {container.name}: {e}")
            except Exception as e:
                logger.error(f"Failed to prune containers: {e}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _prune)
