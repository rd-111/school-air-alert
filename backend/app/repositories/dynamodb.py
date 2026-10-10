"""DynamoDB repository adapters and numeric serialization."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config


def _dynamodb_resource(region_name: str):
    return boto3.resource(
        "dynamodb",
        region_name=region_name or None,
        config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1}),
    )


def _to_dynamo(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamo(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamo(item) for item in value]
    if isinstance(value, tuple):
        return [_to_dynamo(item) for item in value]
    return value


def _from_dynamo(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _from_dynamo(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_from_dynamo(item) for item in value]
    return value


class DynamoSchoolRepository:
    def __init__(self, table_name: str, region_name: str):
        if not table_name:
            raise ValueError("SCHOOLS_TABLE must be configured outside memory mode")
        self.table = _dynamodb_resource(region_name).Table(table_name)

    def list_all(self) -> list[dict]:
        result = self.table.scan()
        items = list(result.get("Items", []))
        while result.get("LastEvaluatedKey"):
            result = self.table.scan(ExclusiveStartKey=result["LastEvaluatedKey"])
            items.extend(result.get("Items", []))
        return [_from_dynamo(item) for item in items]

    def get(self, school_id: str) -> dict | None:
        response = self.table.get_item(Key={"school_id": school_id})
        item = response.get("Item")
        return _from_dynamo(item) if item else None

    def put(self, school: dict) -> None:
        self.table.put_item(Item=_to_dynamo(school))


class DynamoHistoryRepository:
    def __init__(self, table_name: str, region_name: str):
        if not table_name:
            raise ValueError("HISTORY_TABLE must be configured outside memory mode")
        self.table = _dynamodb_resource(region_name).Table(table_name)

    def put(self, record: dict) -> None:
        self.table.put_item(Item=_to_dynamo(record))

    def get(self, school_id: str, date: str) -> dict | None:
        response = self.table.get_item(Key={"school_id": school_id, "date": date})
        item = response.get("Item")
        return _from_dynamo(item) if item else None

    def latest(self, school_id: str) -> dict | None:
        response = self.table.query(
            KeyConditionExpression=Key("school_id").eq(school_id),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get("Items", [])
        return _from_dynamo(items[0]) if items else None

    def list_recent(self, school_id: str, start_date: str, end_date: str) -> list[dict]:
        response = self.table.query(
            KeyConditionExpression=Key("school_id").eq(school_id)
            & Key("date").between(start_date, end_date),
            ScanIndexForward=False,
        )
        return [_from_dynamo(item) for item in response.get("Items", [])]


class DynamoSubscriberRepository:
    def __init__(self, table_name: str, region_name: str):
        if not table_name:
            raise ValueError("SUBSCRIBERS_TABLE must be configured outside memory mode")
        self.table = _dynamodb_resource(region_name).Table(table_name)

    def put(self, subscriber: dict) -> None:
        self.table.put_item(Item=_to_dynamo(subscriber))

    def list_by_school(self, school_id: str) -> list[dict]:
        response = self.table.query(
            KeyConditionExpression=Key("school_id").eq(school_id)
        )
        items = list(response.get("Items", []))
        while response.get("LastEvaluatedKey"):
            response = self.table.query(
                KeyConditionExpression=Key("school_id").eq(school_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        return [_from_dynamo(item) for item in items]

    def find_by_contact(self, contact: str) -> list[dict]:
        response = self.table.scan(FilterExpression=Attr("contact").eq(contact))
        items = list(response.get("Items", []))
        while response.get("LastEvaluatedKey"):
            response = self.table.scan(
                FilterExpression=Attr("contact").eq(contact),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        return [_from_dynamo(item) for item in items]

    def delete(self, school_id: str, contact: str) -> None:
        self.table.delete_item(Key={"school_id": school_id, "contact": contact})
