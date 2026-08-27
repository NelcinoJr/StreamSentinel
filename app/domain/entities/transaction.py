"""
Entidade de domínio — pura, sem SQLAlchemy, sem FastAPI, sem Redis.

Paralelo Zend:
  Não é TableGateway nem row do banco.
  É o "objeto de negócio" (como uma Entity de domínio),
  independente de Zend\\Db ou Doctrine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class TransactionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass(slots=True)
class Transaction:
    """Agregado central do StreamSentinel (ingestão de transação)."""

    external_id: str
    amount: Decimal
    currency: str
    occurred_at: datetime
    id: UUID = field(default_factory=uuid4)
    status: TransactionStatus = TransactionStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def mark_accepted(self) -> None:
        """Regra de domínio: aceita para processamento assíncrono."""
        self.status = TransactionStatus.ACCEPTED

    def mark_processed(self) -> None:
        self.status = TransactionStatus.PROCESSED

    def mark_failed(self) -> None:
        self.status = TransactionStatus.FAILED
