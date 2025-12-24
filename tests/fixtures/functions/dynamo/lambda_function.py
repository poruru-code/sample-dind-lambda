"""
DynamoDB 互換 Lambda (ScyllaDB)

DynamoDB API 操作を提供するシンプルな Lambda 関数。
"""

import json
import uuid
import time
import logging
import boto3
from common.utils import handle_ping, create_response
from trace_bridge import hydrate_trace_id

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = "e2e-test-table"


@hydrate_trace_id
def lambda_handler(event, context):
    # RIE Heartbeat
    if ping_response := handle_ping(event):
        return ping_response

    logger.info(f"Received event: {json.dumps(event)}")

    try:
        dynamodb = boto3.client("dynamodb")

        # Create item
        item_id = str(uuid.uuid4())
        timestamp = int(time.time())
        item = {
            "id": {"S": item_id},
            "timestamp": {"N": str(timestamp)},
            "message": {"S": "Hello from ScyllaDB Lambda"},
        }

        logger.info(f"Putting item: {item}")
        dynamodb.put_item(TableName=TABLE_NAME, Item=item)

        # Get item
        logger.info(f"Getting item: {item_id}")
        response = dynamodb.get_item(TableName=TABLE_NAME, Key={"id": {"S": item_id}})
        retrieved = response.get("Item", {})

        return create_response(
            body={"success": True, "item_id": item_id, "retrieved_item": retrieved}
        )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return create_response(status_code=500, body={"success": False, "error": str(e)})
