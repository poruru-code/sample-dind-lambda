import grpc
import logging
from typing import List, Optional

from services.common.models.internal import WorkerInfo
from services.gateway.pb import agent_pb2, agent_pb2_grpc
from services.gateway.core.exceptions import (
    OrchestratorUnreachableError,
    OrchestratorTimeoutError,
    ContainerStartError,
)
from services.gateway.services.lambda_invoker import WorkerState
from services.gateway.services.function_registry import FunctionRegistry

logger = logging.getLogger("gateway.grpc_backend")


class GrpcBackend:
    def __init__(self, agent_address: str, function_registry: Optional[FunctionRegistry] = None):
        self.channel = grpc.aio.insecure_channel(agent_address)
        self.stub = agent_pb2_grpc.AgentServiceStub(self.channel)
        self.function_registry = function_registry

    async def acquire_worker(self, function_name: str) -> WorkerInfo:
        """
        gRPC 経由でエージェントからワーカー（コンテナ）を取得
        """
        # Get environment variables from FunctionRegistry
        env = {}
        image = ""
        if self.function_registry:
            func_config = self.function_registry.get_function_config(function_name)
            if func_config:
                env = func_config.get("environment", {})
                image = func_config.get("image", "")

        req = agent_pb2.EnsureContainerRequest(
            function_name=function_name,
            image=image,
            env=env,
        )
        try:
            resp = await self.stub.EnsureContainer(req)
            return WorkerInfo(
                id=resp.id, name=resp.name, ip_address=resp.ip_address, port=resp.port
            )
        except grpc.RpcError as e:
            self._handle_grpc_error(e, function_name)

    async def release_worker(self, function_name: str, worker: WorkerInfo) -> None:
        """
        ワーカーを返却（Agent側で管理するため、何もしない場合が多い）
        """
        pass

    async def evict_worker(self, function_name: str, worker: WorkerInfo) -> None:
        """
        ワーカーを明示的に破壊
        """
        req = agent_pb2.DestroyContainerRequest(function_name=function_name, container_id=worker.id)
        try:
            await self.stub.DestroyContainer(req)
        except grpc.RpcError as e:
            # Eviction errors are logged but usually don't block
            logger.error(f"Failed to evict worker {worker.id}: {e}")

    async def list_workers(self) -> List[WorkerState]:
        """
        Agent から全ワーカーの状態を取得 (Janitor 用)
        """
        req = agent_pb2.ListContainersRequest()
        try:
            resp = await self.stub.ListContainers(req)
            return [
                WorkerState(
                    container_id=c.container_id,
                    function_name=c.function_name,
                    status=c.status,
                    last_used_at=c.last_used_at,
                )
                for c in resp.containers
            ]
        except grpc.RpcError as e:
            logger.error(f"Failed to list workers: {e}")
            return []

    def _handle_grpc_error(self, e: grpc.RpcError, function_name: str):
        code = e.code()
        # gRPC aio errors often have a .details() method
        details = getattr(e, "details", lambda: str(e))()

        if code == grpc.StatusCode.UNAVAILABLE:
            raise OrchestratorUnreachableError(f"Agent unavailable: {details}")
        elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise OrchestratorTimeoutError(f"Agent request timed out: {details}")
        elif code == grpc.StatusCode.RESOURCE_EXHAUSTED:
            raise ContainerStartError(function_name, f"Agent resource exhausted: {details}")
        else:
            logger.error(f"Unexpected gRPC error: {code} - {details}")
            raise e

    async def close(self):
        await self.channel.close()
