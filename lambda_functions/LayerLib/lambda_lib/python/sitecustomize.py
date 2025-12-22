"""
sitecustomize.py - Transparent boto3 Endpoint Redirection

Pythonインタプリタ起動時に自動ロードされ、boto3.client() を透過的にローカルエンドポイントへリダイレクト。
"""

import os
import json
import time
import boto3
from botocore.config import Config

_original_boto3_client = boto3.client

# サービス設定
SERVICE_CONFIG = {
    's3': {
        'env_var': 'S3_ENDPOINT',
        'config': Config(s3={'addressing_style': 'path'}, signature_version='s3v4'),
    },
    'dynamodb': {
        'env_var': 'DYNAMODB_ENDPOINT',
        'config': Config(retries={'max_attempts': 10, 'mode': 'standard'}, connect_timeout=5, read_timeout=5),
    },
}

def _patched_put_log_events(self, **kwargs):
    """PutLogEvents を標準出力への JSON 出力に差し替える"""
    try:
        log_group = kwargs.get('logGroupName', 'unknown')
        log_stream = kwargs.get('logStreamName', 'unknown')
        log_events = kwargs.get('logEvents', [])
        
        # log_group からコンテナ名を推定
        container_name = "unknown"
        if log_group.startswith("/lambda/"):
            func_name = log_group[len("/lambda/"):]
            if func_name.endswith("-test"):
                func_name = func_name[:-5]
            container_name = f"lambda-{func_name}"
        
        if container_name.startswith("/"):
            container_name = container_name[1:]
        
        print(f"[sitecustomize] Estimated container_name: '{container_name}' (log_group: '{log_group}')")

        # LOG_LEVEL によるフィルタリング
        current_log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
        level_map = {
            'DEBUG': 10,
            'INFO': 20,
            'WARNING': 30,
            'ERROR': 40,
            'CRITICAL': 50
        }
        threshold = level_map.get(current_log_level, 20)

        for event in log_events:
            msg = event.get('message', '')
            ts = event.get('timestamp', int(time.time() * 1000))
            
            # ログレベルのパース
            level = "INFO"
            clean_msg = msg
            for lvl in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                if msg.startswith(f"[{lvl}]"):
                    level = lvl
                    clean_msg = msg[len(f"[{lvl}]"):].lstrip()
                    break
            
            # フィルタリング判定
            if level_map.get(level, 20) < threshold:
                continue

            log_entry = {
                "_time": ts / 1000.0,
                "level": level,
                "message": clean_msg,
                "log_group": log_group,
                "log_stream": log_stream,
                "logger": "boto3.mock",
                "container_name": container_name,
            }
            print(json.dumps(log_entry, ensure_ascii=False))
            
        return {"nextSequenceToken": "mock-token"}
    except Exception as e:
        print(f"[sitecustomize] Error in _patched_put_log_events: {e}")
        raise e


def _patched_boto3_client(service_name, *args, **kwargs):
    try:
        # Logs サービスの場合はさらに _make_api_call を差し替える（stdoutモード & ローカルモック）
        # エンドポイント設定に関係なく適用
        if service_name == 'logs':
            print("[sitecustomize] Creating original boto3 client for logs (local mock mode)...")
            client = _original_boto3_client(service_name, *args, **kwargs)
            
            print("[sitecustomize] Patching _make_api_call for logs client...")
            _original_make_api_call = client._make_api_call
            
            def _patched_make_api_call(operation_name, api_params):
                if operation_name == 'PutLogEvents':
                    return _patched_put_log_events(client, **api_params)
                
                # 管理系操作はスタブレスポンスを返す
                if operation_name in ('CreateLogGroup', 'CreateLogStream', 'DeleteLogGroup', 'DeleteLogStream'):
                    return {}
                
                if operation_name == 'DescribeLogGroups':
                    return {'logGroups': []}
                
                if operation_name == 'DescribeLogStreams':
                    return {'logStreams': []}

                return _original_make_api_call(operation_name, api_params)
            
            client._make_api_call = _patched_make_api_call
            print("[sitecustomize] boto3.client('logs') patched (Full Local Mock mode)")
            return client

        service_cfg = SERVICE_CONFIG.get(service_name)
        if service_cfg:
            endpoint = os.environ.get(service_cfg['env_var'])
            if endpoint:
                # 基本的なエンドポイントリダイレクト設定
                kwargs['endpoint_url'] = endpoint
                kwargs['verify'] = False
                if service_cfg['config']:
                    existing = kwargs.get('config')
                    kwargs['config'] = existing.merge(service_cfg['config']) if existing else service_cfg['config']
                
                # クライアント生成
                print(f"[sitecustomize] Creating original boto3 client for {service_name}...")
                client = _original_boto3_client(service_name, *args, **kwargs)
                print(f"[sitecustomize] boto3.client('{service_name}') redirected to {endpoint}")
                return client

        return _original_boto3_client(service_name, *args, **kwargs)
    except Exception as e:
        print(f"[sitecustomize] Error in _patched_boto3_client for {service_name}: {e}")
        import traceback
        traceback.print_exc()
        raise e

boto3.client = _patched_boto3_client
