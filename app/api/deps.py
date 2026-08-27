"""
Composition root — monta dependências (estilo ServiceManager do Zend).

Aqui é o ÚNICO lugar que conhece Redis concreto + Use Case.
Controllers pedem via Depends; domínio não conhece infra.
"""

from __future__ import annotations

import os

from redis.asyncio import Redis

from app.infrastructure.queue.redis_publisher import RedisEventPublisher
from app.use_cases.ingest_transaction import IngestTransactionUseCase

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis = Redis.from_url(url, decode_responses=True)
    return _redis


def build_ingest_use_case() -> IngestTransactionUseCase:
    publisher = RedisEventPublisher(get_redis())
    return IngestTransactionUseCase(publisher=publisher)
