"""In-memory record repository (dev): records commit before cursors advance."""
from __future__ import annotations
from reddit_camofox_client.domain_records.models import NormalizedPostRecord


class InMemoryRecordRepository:
    def __init__(self) -> None:
        self._store: dict[str, NormalizedPostRecord] = {}

    async def save(self, record: NormalizedPostRecord) -> None:
        self._store[record.record_id] = record

    async def list(self) -> list[NormalizedPostRecord]:
        return list(self._store.values())
