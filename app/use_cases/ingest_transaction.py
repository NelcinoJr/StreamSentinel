"""
Caso de uso: validar rápido + publicar na fila + HTTP 202.

Paralelo Zend:
  Application Service / Domain Service chamado pelo Controller.
  Controller NÃO fala com Redis nem com Repository direto —
  só chama este "serviço" (como um Service injetado no ZF2/3).

Fluxo:
  1. Monta a Entity de domínio
  2. mark_accepted()
  3. Publica evento no Redis (worker persiste depois)
  4. Retorna payload para o Controller responder 202
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.entities.transaction import Transaction
from app.domain.ports.queue import EventPublisherPort

TRANSACTION_INGEST_CHANNEL = "streamsentinel:transactions:ingest"


@dataclass(frozen=True, slots=True)
class IngestTransactionInput:
    """DTO de entrada do caso de uso (já validado pelo Pydantic na borda)."""

    external_id: str
    amount: Decimal
    currency: str
    occurred_at: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class IngestTransactionResult:
    """O que o Controller usa para montar a resposta 202."""

    transaction_id: UUID
    status: str
    message: str


class IngestTransactionUseCase:
    def __init__(self, publisher: EventPublisherPort) -> None:
        self._publisher = publisher

    async def execute(
        self,
        data: IngestTransactionInput,
    ) -> IngestTransactionResult:
        transaction = Transaction(
            external_id=data.external_id,
            amount=data.amount,
            currency=data.currency.upper(),
            occurred_at=data.occurred_at,
            metadata=data.metadata,
        )
        transaction.mark_accepted()

        await self._publisher.publish(
            TRANSACTION_INGEST_CHANNEL,
            {
                "id": str(transaction.id),
                "external_id": transaction.external_id,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "occurred_at": transaction.occurred_at.isoformat(),
                "status": transaction.status.value,
                "metadata": transaction.metadata,
                "created_at": transaction.created_at.isoformat(),
            },
        )

        return IngestTransactionResult(
            transaction_id=transaction.id,
            status=transaction.status.value,
            message="Transaction accepted for asynchronous processing",
        )
