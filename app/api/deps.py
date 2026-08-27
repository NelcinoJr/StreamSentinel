"""
Composition root — monta dependências (estilo ServiceManager do Zend).

Único lugar que conhece Redis, MySQL session, Finder e Use Cases concretos.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.finders.transaction_finder_impl import (
    TransactionFinderImpl,
)
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.queue.redis_publisher import RedisEventPublisher
from app.use_cases.get_transaction import GetTransactionUseCase
from app.use_cases.ingest_transaction import IngestTransactionUseCase
from app.use_cases.list_transactions import ListTransactionsUseCase

_redis: Redis | None = None


def get_redis() -> Redis:
    """Cliente Redis singleton (fila)."""
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis = Redis.from_url(url, decode_responses=True)
    return _redis


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """
    Abre uma session MySQL por request e fecha no fim.
    No Zend: pedir Adapter/EntityManager no início da action.
    yield = FastAPI Depends (entrega e depois limpa).
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session


def build_ingest_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> IngestTransactionUseCase:
    """
    Factory da ingestão:
      - Finder → checa external_id (idempotência)
      - Publisher → enfileira no Redis
    """
    publisher = RedisEventPublisher(get_redis())
    finder = TransactionFinderImpl(session)
    return IngestTransactionUseCase(publisher=publisher, finder=finder)


def build_get_transaction_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> GetTransactionUseCase:
    """Finder concreto + Use Case de busca por id."""
    finder = TransactionFinderImpl(session)
    return GetTransactionUseCase(finder=finder)


def build_list_transactions_use_case(
    session: AsyncSession = Depends(get_db_session),
) -> ListTransactionsUseCase:
    """Finder concreto + Use Case de listagem por período."""
    finder = TransactionFinderImpl(session)
    return ListTransactionsUseCase(finder=finder)
