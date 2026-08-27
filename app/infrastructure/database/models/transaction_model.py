"""
Modelo ORM SQLAlchemy — mapeamento tabela ↔ linha.

Paralelo Zend:
  Como HydratingResultSet / Doctrine Entity mapping,
  NÃO é a Entity de domínio. Infra traduz Domain ↔ DB.

IMPORTANTE ( ContaÁgil ):
  Antes de CREATE TABLE / migration real, validar schema via MCP mysql-dev.
  Este arquivo é a proposta estrutural; conexão MCP falhou (Access denied)
  na inspeção inicial — revalidar antes de aplicar DDL.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TransactionModel(Base):
    """
    Tabela proposta: transactions

    Índices recomendados (relatórios + idempotência):
      - uq_transactions_external_id  → deduplicação
      - ix_transactions_occurred_at  → list_by_period (Finder)
      - ix_transactions_status       → filas/ops
    """

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("uq_transactions_external_id", "external_id", unique=True),
        Index("ix_transactions_occurred_at", "occurred_at"),
        Index("ix_transactions_status", "status"),
    )

    def to_read_dict(self) -> dict[str, Any]:
        """Read model simples para o Finder (sem Entity de domínio)."""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def from_domain_payload(payload: dict[str, Any]) -> TransactionModel:
        """Factory usada pelo Repository a partir do evento da fila."""
        return TransactionModel(
            id=str(payload["id"]) if not isinstance(payload["id"], UUID) else str(payload["id"]),
            external_id=payload["external_id"],
            amount=Decimal(str(payload["amount"])),
            currency=payload["currency"],
            status=payload["status"],
            occurred_at=payload["occurred_at"]
            if isinstance(payload["occurred_at"], datetime)
            else datetime.fromisoformat(payload["occurred_at"]),
            metadata_json=payload.get("metadata") or {},
        )
