"""
Worker de ingestão — consome a fila Redis e persiste no MySQL.

Paralelo Zend/PHP:
  Consumer Beanstalkd: reserve → process → delete.
  Se falhar: release com delay (retry) ou bury (dead-letter).

Aqui:
  BLPOP → process_one → sucesso
  Se falhar: até MAX_ATTEMPTS reenfileira; senão vai pra DLQ.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError

from app.domain.entities.transaction import TransactionStatus
from app.infrastructure.database.models.transaction_model import Base, TransactionModel
from app.infrastructure.database.repositories.transaction_repository_impl import (
    TransactionRepositoryImpl,
)
from app.infrastructure.database.session import get_engine, get_session_factory
from app.use_cases.ingest_transaction import (
    TRANSACTION_INGEST_CHANNEL,
    TRANSACTION_INGEST_DLQ,
)

# Quantas vezes tenta de novo antes de mandar pra fila de falhas
MAX_ATTEMPTS = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
logger = logging.getLogger("transaction_ingest_worker")

_running = True


def _handle_stop(signum: int, frame: Any) -> None:
    """docker stop / Ctrl+C — para depois do job atual."""
    global _running
    logger.info("Sinal %s recebido — encerrando após o job atual", signum)
    _running = False


async def ensure_schema() -> None:
    """CREATE TABLE IF NOT EXISTS (só ambiente local Docker)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Schema OK (tabela %s)", TransactionModel.__tablename__)


async def process_one(payload: dict[str, Any]) -> None:
    """
    Processa UM job.
    IntegrityError = external_id já no banco → ignora (idempotente).
    """
    from uuid import UUID

    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            repo = TransactionRepositoryImpl(session)
            await repo.save_from_event(payload)
            await repo.update_status(
                UUID(str(payload["id"])),
                TransactionStatus.PROCESSED.value,
            )
    except IntegrityError:
        # Unique de external_id — job repetido / corrida; não é falha fatal
        logger.warning(
            "Já existia no MySQL (idempotente) external_id=%s",
            payload.get("external_id"),
        )
        return

    logger.info(
        "Persistido id=%s external_id=%s status=processed",
        payload.get("id"),
        payload.get("external_id"),
    )


async def handle_failure(
    redis: Redis,
    raw: str,
    payload: dict[str, Any] | None,
    error: BaseException,
) -> None:
    """
    Retry ou Dead Letter Queue.

    Paralelo Beanstalkd:
      release = tenta de novo
      bury    = enterra na DLQ pra análise humana
    """
    # Contador interno do job (não faz parte do domínio; só infra da fila)
    attempts = 0
    if payload is not None:
        attempts = int(payload.get("_attempts", 0)) + 1
        payload["_attempts"] = attempts
        payload["_last_error"] = str(error)

    if payload is not None and attempts < MAX_ATTEMPTS:
        # Recoloca no fim da fila principal para nova tentativa
        await redis.rpush(TRANSACTION_INGEST_CHANNEL, json.dumps(payload, default=str))
        logger.warning(
            "Retry %s/%s external_id=%s erro=%s",
            attempts,
            MAX_ATTEMPTS,
            payload.get("external_id"),
            error,
        )
        return

    # Esgotou tentativas (ou JSON inválido) → DLQ
    dead = {
        "raw": raw if payload is None else None,
        "payload": payload,
        "error": str(error),
        "attempts": attempts,
    }
    await redis.rpush(TRANSACTION_INGEST_DLQ, json.dumps(dead, default=str))
    logger.error(
        "Enviado para DLQ (%s) attempts=%s erro=%s",
        TRANSACTION_INGEST_DLQ,
        attempts,
        error,
    )


async def run() -> None:
    """Loop principal do worker."""
    import os

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)

    await ensure_schema()
    logger.info(
        "Ouvindo fila=%s | DLQ=%s | max_attempts=%s",
        TRANSACTION_INGEST_CHANNEL,
        TRANSACTION_INGEST_DLQ,
        MAX_ATTEMPTS,
    )

    while _running:
        item = await redis.blpop(TRANSACTION_INGEST_CHANNEL, timeout=5)
        if item is None:
            continue

        _list_name, raw = item
        payload: dict[str, Any] | None = None
        try:
            payload = json.loads(raw)
            await process_one(payload)
        except Exception as exc:
            await handle_failure(redis, raw, payload, exc)

    await redis.aclose()
    logger.info("Worker finalizado")


def main() -> None:
    """Entrypoint: python -m app.workers.transaction_ingest_worker"""
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)
    asyncio.run(run())


if __name__ == "__main__":
    main()
