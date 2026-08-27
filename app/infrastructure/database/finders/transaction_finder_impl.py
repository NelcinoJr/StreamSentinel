"""
Finder (leitura) — SELECTs otimizados / relatórios.

Paralelo Zend:
  Query Object ou TableGateway::select com joins/filtros.
  Retorna dict (read model), não a Entity de escrita.
  Controller de consulta → Use Case de query → Finder.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.transaction_model import TransactionModel


class TransactionFinderImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, transaction_id: UUID) -> dict[str, Any] | None:
        stmt = select(TransactionModel).where(
            TransactionModel.id == str(transaction_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_read_dict() if model else None

    async def find_by_external_id(self, external_id: str) -> dict[str, Any] | None:
        stmt = select(TransactionModel).where(
            TransactionModel.external_id == external_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_read_dict() if model else None

    async def list_by_period(
        self,
        started_at: datetime,
        ended_at: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        # Usa ix_transactions_occurred_at — validar plano via EXPLAIN no mysql-dev
        stmt = (
            select(TransactionModel)
            .where(TransactionModel.occurred_at >= started_at)
            .where(TransactionModel.occurred_at <= ended_at)
            .order_by(TransactionModel.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [row.to_read_dict() for row in rows]
