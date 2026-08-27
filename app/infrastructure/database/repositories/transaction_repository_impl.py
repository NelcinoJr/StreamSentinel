"""
Repository (escrita) — INSERT/UPDATE assíncronos.

Paralelo Zend:
  TableGateway::insert / update, ou Mapper::save().
  Não faz relatório; só persistência transacional (CQRS Command).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.transaction import Transaction
from app.infrastructure.database.models.transaction_model import TransactionModel


class TransactionRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, transaction: Transaction) -> Transaction:
        model = TransactionModel(
            id=str(transaction.id),
            external_id=transaction.external_id,
            amount=transaction.amount,
            currency=transaction.currency,
            status=transaction.status.value,
            occurred_at=transaction.occurred_at,
            metadata_json=transaction.metadata,
            created_at=transaction.created_at,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return transaction

    async def save_from_event(self, payload: dict) -> None:
        """Usado pelo Worker: persiste o payload publicado no Redis."""
        model = TransactionModel.from_domain_payload(payload)
        self._session.add(model)
        await self._session.commit()

    async def update_status(self, transaction_id: UUID, status: str) -> None:
        stmt = (
            update(TransactionModel)
            .where(TransactionModel.id == str(transaction_id))
            .values(status=status)
        )
        await self._session.execute(stmt)
        await self._session.commit()
