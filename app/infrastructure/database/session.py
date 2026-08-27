"""
Fábrica de conexão MySQL (async).

Paralelo Zend:
  Como configurar o Adapter Zend\\Db no ServiceManager
  (dsn/host/user/pass) e obter uma conexão/session por request/job.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# URL padrão = serviço "mysql" do docker-compose (hostname interno)
_DEFAULT_URL = (
    "mysql+asyncmy://streamsentinel:streamsentinel@mysql:3306/streamsentinel"
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    """Lê DATABASE_URL do ambiente (application.ini → getenv)."""
    return os.getenv("DATABASE_URL", _DEFAULT_URL)


def get_engine() -> AsyncEngine:
    """
    Cria o engine uma vez (singleton).
    Engine = pool de conexões com o MySQL.
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            pool_pre_ping=True,  # testa conexão antes de usar (evita stale)
            echo=False,  # True = loga SQL (debug); False = silencioso
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Factory de sessions.
    No Zend: cada script pedia $adapter; aqui cada job pede uma AsyncSession.
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory
