"""
Auto-Scaling E2E Tests
Tests the Pool behavior, Reuse, and Basic Scaling.
"""

import pytest
import subprocess
import time
import httpx
from tests.conftest import call_api, AUTH_USER

def get_container_ids(function_name):
    """Get container IDs for a function name pattern"""
    cmd = ["docker", "ps", "-q", "-f", f"name=lambda-{function_name}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip().splitlines()

class TestAutoScaling:
    def test_pool_provision_and_reuse(self, auth_token):
        """
        Verify that:
        1. First invocation provisions a container.
        2. Second invocation reuses the SAME container.
        """
        # 1. First Invocation
        response = call_api("/api/echo", auth_token, {"message": "autoscale-1"})
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Echo: autoscale-1"

        # Check Container ID
        ids_1 = get_container_ids("echo")
        assert len(ids_1) == 1, f"Expected 1 echo container, found {len(ids_1)}: {ids_1}"
        container_id_1 = ids_1[0]

        # 2. Second Invocation
        response = call_api("/api/echo", auth_token, {"message": "autoscale-2"})
        assert response.status_code == 200
        
        # Check Container ID again
        ids_2 = get_container_ids("echo")
        assert len(ids_2) == 1
        container_id_2 = ids_2[0]

        # Assert Reuse
        assert container_id_1 == container_id_2, "Container should be reused in Pool Mode"

    def test_concurrent_queueing(self, auth_token):
        """
        With MAX_CAPACITY=1, concurrent requests should be handled.
        (They will be serialized by the semaphore).
        """
        import concurrent.futures

        def invoke(msg):
            return call_api("/api/echo", auth_token, {"message": msg})

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(invoke, f"concurrent-{i}") for i in range(3)
            ]
            results = [f.result() for f in futures]

        for res in results:
            assert res.status_code == 200
            assert "Echo: concurrent-" in res.json()["message"]
        
        # Still 1 container
        ids = get_container_ids("echo")
        assert len(ids) == 1

