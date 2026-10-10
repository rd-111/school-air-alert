import pytest
from botocore.exceptions import ClientError

from app.repositories import notification_runs
from app.repositories.notification_runs import DynamoNotificationRunRepository


class FakeTable:
    def __init__(self, error=None):
        self.error = error
        self.put = None
        self.deleted = None

    def put_item(self, **kwargs):
        self.put = kwargs
        if self.error:
            raise self.error

    def delete_item(self, **kwargs):
        self.deleted = kwargs


class FakeResource:
    def __init__(self, table):
        self.table = table
        self.table_name = None

    def Table(self, name):
        self.table_name = name
        return self.table


def make_repository(monkeypatch, table):
    resource = FakeResource(table)
    monkeypatch.setattr(
        notification_runs.boto3,
        "resource",
        lambda *_args, **_kwargs: resource,
    )
    return DynamoNotificationRunRepository("notification-runs", "ap-south-1"), resource


def test_dynamodb_claim_is_conditional_and_release_deletes_the_run(monkeypatch):
    table = FakeTable()
    repository, resource = make_repository(monkeypatch, table)

    assert repository.claim("run-hash", 1_800_000_000) is True
    repository.release("run-hash")

    assert resource.table_name == "notification-runs"
    assert table.put == {
        "Item": {"run_id": "run-hash", "expires_at": 1_800_000_000},
        "ConditionExpression": "attribute_not_exists(run_id)",
    }
    assert table.deleted == {"Key": {"run_id": "run-hash"}}


def test_dynamodb_duplicate_claim_returns_false(monkeypatch):
    duplicate = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
    )
    table = FakeTable(error=duplicate)
    repository, _resource = make_repository(monkeypatch, table)

    assert repository.claim("run-hash", 1_800_000_000) is False


def test_dynamodb_claim_propagates_non_duplicate_storage_errors(monkeypatch):
    failure = ClientError({"Error": {"Code": "AccessDeniedException"}}, "PutItem")
    repository, _resource = make_repository(monkeypatch, FakeTable(error=failure))

    with pytest.raises(ClientError) as error:
        repository.claim("run-hash", 1_800_000_000)
    assert error.value is failure
