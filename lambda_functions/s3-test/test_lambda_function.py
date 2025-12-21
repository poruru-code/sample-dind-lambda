import json
import io
import sys
import unittest
from unittest.mock import MagicMock

# Mock dependencies BEFORE importing lambda_function
sys.modules["s3_util"] = MagicMock()
sys.modules["boto3"] = MagicMock()

# Add the directory to sys.path
sys.path.append("lambda_functions/s3-test")

import lambda_function  # noqa: E402


class TestLambdaFunction(unittest.TestCase):
    def test_lambda_handler_logs_structured_json(self):
        """
        Test that lambda_handler prints a structured JSON log
        containing request_id, level, and message.
        """
        event = {
            "requestContext": {"requestId": "test-request-id-123"},
            "Action": "Unknown",
            "Key": "test-key",
        }
        context = MagicMock()

        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            lambda_function.lambda_handler(event, context)
        finally:
            sys.stdout = sys.__stdout__  # Restore stdout

        output = captured_output.getvalue()

        # Parse output line by line to find the JSON log
        found_json_log = False
        for line in output.splitlines():
            try:
                log_entry = json.loads(line)
                # Check for required fields
                if (
                    log_entry.get("request_id") == "test-request-id-123"
                    and log_entry.get("level") == "INFO"
                    and "message" in log_entry
                ):
                    found_json_log = True
                    break
            except json.JSONDecodeError:
                continue

        self.assertTrue(
            found_json_log,
            "Structured JSON log with request_id not found in stdout. Output was:\n" + output,
        )


if __name__ == "__main__":
    unittest.main()
