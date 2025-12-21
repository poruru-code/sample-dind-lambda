"""
S3互換ストレージ (RustFS) 接続ユーティリティ

Lambda関数からRustFSへのS3互換APIアクセスを提供します。
"""

import boto3
import botocore
import logging
from .layer_config import config

logger = logging.getLogger(__name__)


def init_storage():
    """
    S3互換ストレージクライアントを初期化して返す
    """
    s3_endpoint = config.S3_ENDPOINT

    s3_client = boto3.client(
        "s3",
        endpoint_url=s3_endpoint,
        aws_access_key_id=config.RUSTFS_ROOT_USER,
        aws_secret_access_key=config.RUSTFS_ROOT_PASSWORD,
        region_name=config.AWS_REGION,
        config=botocore.config.Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )

    logger.info(f"S3 client initialized with endpoint: {s3_endpoint}")
    return s3_client


def get_object(bucket: str, key: str) -> bytes:
    """
    S3からオブジェクトを取得

    Args:
        bucket: バケット名
        key: オブジェクトキー

    Returns:
        bytes: オブジェクトの内容
    """
    client = init_storage()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def put_object(
    bucket: str, key: str, body: bytes, content_type: str = "application/octet-stream"
) -> dict:
    """
    S3にオブジェクトをアップロード

    Args:
        bucket: バケット名
        key: オブジェクトキー
        body: アップロードするデータ
        content_type: Content-Type

    Returns:
        dict: アップロード結果
    """
    client = init_storage()
    return client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)


def list_objects(bucket: str, prefix: str = "") -> list:
    """
    S3バケット内のオブジェクト一覧を取得

    Args:
        bucket: バケット名
        prefix: プレフィックス（フィルタ）

    Returns:
        list: オブジェクト一覧
    """
    client = init_storage()
    response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    return response.get("Contents", [])


def create_bucket(bucket: str) -> dict:
    """
    S3バケットを作成

    Args:
        bucket: バケット名

    Returns:
        dict: 作成結果
    """
    client = init_storage()
    try:
        return client.create_bucket(
            Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
    except client.exceptions.BucketAlreadyOwnedByYou:
        logger.info(f"Bucket {bucket} already exists")
        return {"Bucket": bucket}
