"""
Echo Lambda: シンプルな応答のみを行う軽量 Lambda

S3/DynamoDB など外部依存なしで Lambda 呼び出しをテスト可能。
"""

import json
import os
from datetime import datetime, timezone
from common.utils import handle_ping, create_response, parse_event_body


def lambda_handler(event, context):
    trace_id = os.environ.get("_X_AMZN_TRACE_ID", "not-found")
    # RIE Heartbeat
    if ping_response := handle_ping(event):
        return ping_response

    body = parse_event_body(event)
    username = (
        event.get("requestContext", {}).get("authorizer", {}).get("cognito:username", "anonymous")
    )

    message = f"Echo: {body.get('message', 'Hello')}"

    # 構造化ログを出力 (VictoriaLogs 検索用)
    # sitecustomize のフックにより trace_id, container_name, job が自動付与されるが、
    # 明示的にも出力して一貫性を検証する
    log_entry = {
        "_time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": "INFO",
        "trace_id": trace_id,
        "message": message,
        "function": "lambda-echo",
    }
    print(json.dumps(log_entry))

    # DEBUG ログ (テスト要件)
    print(json.dumps({**log_entry, "level": "DEBUG", "message": "Debug log for quality test"}))

    return create_response(
        body={
            "success": True,
            "message": message,
            "user": username,
        }
    )
