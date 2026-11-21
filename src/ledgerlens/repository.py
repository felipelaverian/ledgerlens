"""Where processed documents are stored: DynamoDB in AWS, memory for local runs and tests."""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from .models import Document


class Repository(Protocol):
    def save(self, doc: Document) -> None: ...
    def all(self) -> list[dict]: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def save(self, doc: Document) -> None:
        self.items[uuid4().hex] = doc.to_dict()

    def all(self) -> list[dict]:
        return list(self.items.values())


class DynamoDBRepository:
    def __init__(self, table_name: str, resource=None):
        if resource is None:
            import boto3  # deferred import

            resource = boto3.resource("dynamodb")
        self._table = resource.Table(table_name)

    def save(self, doc: Document) -> None:
        item = doc.to_dict()
        item["id"] = uuid4().hex
        self._table.put_item(Item=item)

    def all(self) -> list[dict]:
        response = self._table.scan()
        items = response["Items"]
        while "LastEvaluatedKey" in response:
            response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response["Items"])
        return items
