"""
Testes do Use Case de ingestão (sem Redis/MySQL reais).

Paralelo Zend: PHPUnit com mocks do ServiceManager
(Finder e Publisher falsos, só em memória).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from app.use_cases.ingest_transaction import (
    TRANSACTION_INGEST_CHANNEL,
    IngestTransactionInput,
    IngestTransactionUseCase,
)


class FakePublisher:
    """Substitui o Redis: guarda o que seria publicado."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        self.messages.append((channel, payload))


class FakeFinder:
    """Substitui o MySQL Finder: devolve 'existing' se configurado."""

    def __init__(self, existing: dict[str, Any] | None = None) -> None:
        self.existing = existing

    async def find_by_id(self, transaction_id: Any) -> dict[str, Any] | None:
        return None

    async def find_by_external_id(self, external_id: str) -> dict[str, Any] | None:
        if self.existing and self.existing.get("external_id") == external_id:
            return self.existing
        return None

    async def list_by_period(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return []


def _sample_input(external_id: str = "TX-TEST-1") -> IngestTransactionInput:
    return IngestTransactionInput(
        external_id=external_id,
        amount=Decimal("10.50"),
        currency="brl",
        occurred_at=datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
        metadata={"origem": "teste"},
    )


@pytest.mark.asyncio
async def test_ingest_novo_publica_na_fila() -> None:
    """Novo external_id → publica no Redis (fake) e already_exists=False."""
    publisher = FakePublisher()
    finder = FakeFinder(existing=None)
    use_case = IngestTransactionUseCase(publisher=publisher, finder=finder)

    result = await use_case.execute(_sample_input("TX-NOVO"))

    assert result.already_exists is False
    assert result.status == "accepted"
    assert len(publisher.messages) == 1
    channel, payload = publisher.messages[0]
    assert channel == TRANSACTION_INGEST_CHANNEL
    assert payload["external_id"] == "TX-NOVO"
    assert payload["currency"] == "BRL"


@pytest.mark.asyncio
async def test_ingest_duplicado_nao_publica() -> None:
    """external_id já existe → already_exists=True e NÃO publica na fila."""
    existing_id = uuid4()
    publisher = FakePublisher()
    finder = FakeFinder(
        existing={
            "id": str(existing_id),
            "external_id": "TX-DUP",
            "status": "processed",
        }
    )
    use_case = IngestTransactionUseCase(publisher=publisher, finder=finder)

    result = await use_case.execute(_sample_input("TX-DUP"))

    assert result.already_exists is True
    assert result.transaction_id == existing_id
    assert result.status == "processed"
    assert publisher.messages == []  # não enfileirou de novo
