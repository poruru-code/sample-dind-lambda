"""
DynamoDB 互換テスト (ScyllaDB)

- DynamoDB API の互換性検証
- ScyllaDB バックエンドでの動作確認
"""

import time

import pytest

from tests.fixtures.conftest import (
    SCYLLA_WAIT_INTERVAL,
    SCYLLA_WAIT_RETRIES,
    call_api,
)


class TestDynamoCompat:
    """DynamoDB 互換性の検証"""

    def test_dynamo_put_get(self, auth_token):
        """E2E: DynamoDB PutItem/GetItem 互換テスト (ScyllaDB)"""
        # ScyllaDBの起動待ち（Lambdaが起動するまでリトライ）
        # WindowsのDocker Desktop (WSL2) ではScyllaDBの起動に3-5分かかる場合がある
        max_retries = SCYLLA_WAIT_RETRIES
        response = None

        for i in range(max_retries):
            response = call_api(
                "/api/dynamo",
                auth_token,
                {"action": "dynamo-test", "bucket": "e2e-test-bucket"},
            )

            if response.status_code == 200:
                break

            print(f"Status: {response.status_code}, Body: {response.text}")

            # 500 (Application Error/DB Not Ready) or 502 (Bad Gateway) -> Retry
            if response.status_code not in [500, 502, 503, 504]:
                break

            print(f"Waiting for Lambda/ScyllaDB... ({i + 1}/{max_retries})")
            time.sleep(SCYLLA_WAIT_INTERVAL)

        if response is None:
            pytest.fail("Lambda integration failed: No response received")

        if response.status_code != 200:
            print(f"Final Failure Response: {response.text}")

        assert response.status_code == 200
        data = response.json()
        print(f"Response Data: {data}")
        assert data["success"] is True
        assert "item_id" in data
        assert "retrieved_item" in data
        assert data["retrieved_item"]["id"]["S"] == data["item_id"]
