"""
Caso de uso: validar + idempotência + publicar na fila.

Paralelo Zend:
  Service que:
    1) consulta se external_id já existe (SELECT / Finder)
    2) se existe → conflito (Controller devolve 409)
    3) se não → enfileira job (Beanstalkd/Redis) → 202
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.entities.transaction import Transaction
from app.domain.ports.finders import TransactionFinderPort
from app.domain.ports.queue import EventPublisherPort

TRANSACTION_INGEST_CHANNEL = "streamsentinel:transactions:ingest"
# Fila de falhas (dead-letter) — jobs que esgotaram as tentativas
TRANSACTION_INGEST_DLQ = "streamsentinel:transactions:ingest:dlq"


@dataclass(frozen=True, slots=True)
class IngestTransactionInput:
    """DTO de entrada (já validado pelo Pydantic)."""

    external_id: str
    amount: Decimal
    currency: str
    occurred_at: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class IngestTransactionResult:
    """
    Resultado para o Controller.
    already_exists=True → Controller responde 409 (não enfileirou).
    """

    transaction_id: UUID
    status: str
    message: str
    already_exists: bool = False


class IngestTransactionUseCase:
    def __init__(
        self,
        publisher: EventPublisherPort,
        finder: TransactionFinderPort,
    ) -> None:
        # publisher = fila (escrita assíncrona)
        # finder = leitura para checar duplicata (CQRS: SELECT no Finder)
        self._publisher = publisher
        self._finder = finder

    async def execute(
        self,
        data: IngestTransactionInput,
    ) -> IngestTransactionResult:
        # --- Idempotência: mesmo external_id não entra de novo ---
        existing = await self._finder.find_by_external_id(data.external_id)
        if existing is not None:
            return IngestTransactionResult(
                transaction_id=UUID(str(existing["id"])),
                status=str(existing["status"]),
                message="Transaction already exists for this external_id",
                already_exists=True,
            )

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
            already_exists=False,
        )
