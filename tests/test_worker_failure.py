"""
Testes de retry / DLQ do Worker (sem Redis real).

Paralelo: unit test do consumer Beanstalkd (release vs bury).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.use_cases.ingest_transaction import (
    TRANSACTION_INGEST_CHANNEL,
    TRANSACTION_INGEST_DLQ,
)
from app.workers.transaction_ingest_worker import MAX_ATTEMPTS, handle_failure


class FakeRedis:
    """Redis mínimo: só rpush + listas em memória."""

    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}

    async def rpush(self, key: str, value: str) -> int:
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])


@pytest.mark.asyncio
async def test_falha_reenfileira_enquanto_houver_tentativas() -> None:
    """1ª falha → volta pra fila principal com _attempts=1."""
    redis = FakeRedis()
    payload: dict[str, Any] = {"id": "abc", "external_id": "TX-R1"}

    await handle_failure(redis, raw="{}", payload=payload, error=RuntimeError("boom"))

    assert TRANSACTION_INGEST_CHANNEL in redis.lists
    assert TRANSACTION_INGEST_DLQ not in redis.lists
    queued = json.loads(redis.lists[TRANSACTION_INGEST_CHANNEL][0])
    assert queued["_attempts"] == 1
    assert "boom" in queued["_last_error"]


@pytest.mark.asyncio
async def test_falha_vai_para_dlq_apos_max_attempts() -> None:
    """Na tentativa MAX_ATTEMPTS → dead-letter queue."""
    redis = FakeRedis()
    # Já vem com MAX_ATTEMPTS-1; o handle_failure soma +1 → MAX
    payload: dict[str, Any] = {
        "id": "abc",
        "external_id": "TX-R3",
        "_attempts": MAX_ATTEMPTS - 1,
    }

    await handle_failure(redis, raw="{}", payload=payload, error=RuntimeError("fail"))

    assert TRANSACTION_INGEST_CHANNEL not in redis.lists
    assert len(redis.lists[TRANSACTION_INGEST_DLQ]) == 1
    dead = json.loads(redis.lists[TRANSACTION_INGEST_DLQ][0])
    assert dead["attempts"] == MAX_ATTEMPTS
    assert dead["payload"]["external_id"] == "TX-R3"
    assert "fail" in dead["error"]


@pytest.mark.asyncio
async def test_json_invalido_vai_direto_para_dlq() -> None:
    """payload=None (json.loads falhou) → DLQ sem retry."""
    redis = FakeRedis()

    await handle_failure(
        redis,
        raw="isto-nao-e-json",
        payload=None,
        error=ValueError("Expecting value"),
    )

    dead = json.loads(redis.lists[TRANSACTION_INGEST_DLQ][0])
    assert dead["raw"] == "isto-nao-e-json"
    assert dead["payload"] is None
    assert dead["attempts"] == 0
