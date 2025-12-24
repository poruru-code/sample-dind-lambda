"""
S3 互換テスト (RustFS/MinIO)

- S3 API の互換性検証
- RustFS バックエンドでの動作確認
"""

import uuid


from tests.fixtures.conftest import call_api


class TestS3Compat:
    """S3 互換性の検証"""

    def test_s3_put_get(self, auth_token):
        """E2E: S3 PutObject/GetObject 互換テスト"""
        # ユニークなキーを生成
        test_key = f"test-object-{uuid.uuid4().hex[:8]}.txt"
        test_content = "Hello from E2E test!"

        # 1. PutObject
        put_response = call_api(
            "/api/s3",
            auth_token,
            {
                "action": "put",
                "bucket": "e2e-test-bucket",
                "key": test_key,
                "body": test_content,
            },
        )
        assert put_response.status_code == 200, f"PutObject failed: {put_response.text}"
        put_data = put_response.json()
        assert put_data["success"] is True

        # 2. GetObject
        get_response = call_api(
            "/api/s3",
            auth_token,
            {
                "action": "get",
                "bucket": "e2e-test-bucket",
                "key": test_key,
            },
        )
        assert get_response.status_code == 200, f"GetObject failed: {get_response.text}"
        get_data = get_response.json()
        assert get_data["success"] is True
        assert get_data["content"] == test_content

    def test_s3_list_objects(self, auth_token):
        """E2E: S3 ListObjects 互換テスト"""
        # ListObjects
        response = call_api(
            "/api/s3",
            auth_token,
            {
                "action": "list",
                "bucket": "e2e-test-bucket",
            },
        )
        assert response.status_code == 200, f"ListObjects failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert "objects" in data or "Contents" in data
