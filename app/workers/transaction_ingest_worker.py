"""
Worker de ingestão — consome a fila Redis e persiste no MySQL.

Paralelo Zend/PHP:
  Um script CLI (`php public/index.php worker ingest`) ou consumer
  Beanstalkd que fica em loop: reserva job → processa → delete job.

Aqui:
  BLPOP na lista Redis → Repository.save_from_event → MySQL.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from typing import Any

from redis.asyncio import Redis

from app.infrastructure.database.models.transaction_model import Base, TransactionModel
from app.infrastructure.database.repositories.transaction_repository_impl import (
    TransactionRepositoryImpl,
)
from app.infrastructure.database.session import get_engine, get_session_factory
from app.use_cases.ingest_transaction import TRANSACTION_INGEST_CHANNEL

# Logger = echo/print estruturado (como error_log no PHP)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
logger = logging.getLogger("transaction_ingest_worker")

# Flag global: False quando receber SIGTERM/SIGINT (docker stop / Ctrl+C)
_running = True


def _handle_stop(signum: int, frame: Any) -> None:
    """Sinal do SO pedindo para parar com elegância."""
    global _running
    logger.info("Sinal %s recebido — encerrando após o job atual", signum)
    _running = False


async def ensure_schema() -> None:
    """
    Cria tabelas se não existirem (ambiente local Docker).

    IMPORTANTE ContaÁgil: em ambiente corporativo validaríamos o schema
    via MCP mysql-dev antes do DDL. Aqui o MCP está sem acesso; usamos
    MySQL local do compose + create_all só para desenvolvimento.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Schema OK (tabela %s)", TransactionModel.__tablename__)


async def process_one(payload: dict[str, Any]) -> None:
    """
    Processa UM job da fila.
    Equivale a: pegou o job do Beanstalkd → TableGateway::insert.
    Depois marca status=processed (regra de domínio concluída).
    """
    from uuid import UUID

    from app.domain.entities.transaction import TransactionStatus

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = TransactionRepositoryImpl(session)
        # Grava com status que veio da fila (accepted)
        await repo.save_from_event(payload)
        # Atualiza para processed = "já persistido com sucesso"
        await repo.update_status(
            UUID(str(payload["id"])),
            TransactionStatus.PROCESSED.value,
        )
    logger.info(
        "Persistido id=%s external_id=%s status=processed",
        payload.get("id"),
        payload.get("external_id"),
    )


async def run() -> None:
    """Loop principal do worker."""
    import os

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)

    await ensure_schema()
    logger.info("Ouvindo fila: %s", TRANSACTION_INGEST_CHANNEL)

    while _running:
        # BLPOP = bloqueia até 5s esperando item (ou timeout)
        # Retorno: [nome_da_lista, json_string] ou None no timeout
        item = await redis.blpop(TRANSACTION_INGEST_CHANNEL, timeout=5)
        if item is None:
            continue  # timeout: volta ao while e checa _running

        _list_name, raw = item
        try:
            payload = json.loads(raw)
            await process_one(payload)
        except Exception:
            # Em produção: dead-letter queue / retry.
            # Aqui: loga e NÃO recoloca (aula — ver o erro no log).
            logger.exception("Falha ao processar job: %s", raw)

    await redis.aclose()
    logger.info("Worker finalizado")


def main() -> None:
    """Entrypoint CLI: python -m app.workers.transaction_ingest_worker"""
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)
    asyncio.run(run())


if __name__ == "__main__":
    main()
