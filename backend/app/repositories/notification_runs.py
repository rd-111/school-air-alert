"""Durable delivery claims that prevent duplicate scheduled notifications."""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class DynamoNotificationRunRepository:
    def __init__(self, table_name: str, region_name: str):
        if not table_name:
            raise ValueError("NOTIFICATION_RUNS_TABLE must be configured")
        resource = boto3.resource(
            "dynamodb",
            region_name=region_name or None,
            config=Config(
                connect_timeout=5,
                read_timeout=10,
                retries={"max_attempts": 1},
            ),
        )
        self.table = resource.Table(table_name)

    def claim(self, run_id: str, expires_at: int) -> bool:
        try:
            self.table.put_item(
                Item={"run_id": run_id, "expires_at": expires_at},
                ConditionExpression="attribute_not_exists(run_id)",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def release(self, run_id: str) -> None:
        self.table.delete_item(Key={"run_id": run_id})
