import logging
from typing import Any
import httpx
import os

from ..client import get_lambda_host
from ..core.exceptions import FunctionNotFoundError, ContainerStartError, LambdaExecutionError

logger = logging.getLogger("gateway.lambda_invoker")


class LambdaInvoker:
    def __init__(self, http_client: httpx.AsyncClient, function_registry: Any):
        """
        Args:
            http_client: Shared httpx.AsyncClient
            function_registry: FunctionRegistry instance
        """
        self.client = http_client
        self.registry = function_registry

    async def invoke_function(
        self, function_name: str, payload: bytes, timeout: int = 300
    ) -> httpx.Response:
        """
        Invokes Lambda function (Async).
        """
        # config check
        func_config = self.registry.get_function_config(function_name)
        if func_config is None:
            raise FunctionNotFoundError(function_name)

        # Prepare env
        env = func_config.get("environment", {}).copy()

        # Resolve Gateway URL (Simple approach for now)
        gateway_internal_url = os.getenv("GATEWAY_INTERNAL_URL", "http://gateway:8080")
        env["GATEWAY_INTERNAL_URL"] = gateway_internal_url

        # Ensure container (via Manager)
        try:
            host = await get_lambda_host(
                function_name=function_name,
                image=func_config.get("image"),
                env=env,
            )
        except Exception as e:
            raise ContainerStartError(function_name, e) from e

        # POST to Lambda RIE
        rie_url = f"http://{host}:8080/2015-03-31/functions/function/invocations"
        logger.info(f"Invoking {function_name} at {rie_url}")

        try:
            response = await self.client.post(
                rie_url,
                content=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            return response
        except httpx.RequestError as e:
            raise LambdaExecutionError(function_name, e) from e


# Backward compatibility or helper if needed? No, we are fully refactoring to DI.
