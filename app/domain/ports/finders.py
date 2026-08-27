"""
Portas (contratos) de leitura — lado Query do CQRS.

Paralelo Zend:
  Separar Finder de Repository é como ter:
    - TableGateway::insert/update  → Repository
    - Relatórios / SELECT otimizado → Finder (Query Object / Read Model)
  No Zend clássico muita gente misturava tudo no Mapper; aqui separamos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class TransactionFinderPort(Protocol):
    """Consultas e relatórios (SELECT). Sem INSERT/UPDATE."""

    async def find_by_id(self, transaction_id: UUID) -> dict[str, Any] | None:
        """Busca pontual por ID (read model, dict serializável)."""
        ...

    async def find_by_external_id(
        self,
        external_id: str,
    ) -> dict[str, Any] | None:
        """Idempotência / deduplicação na leitura."""
        ...

    async def list_by_period(
        self,
        started_at: datetime,
        ended_at: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Relatório por intervalo — índices em occurred_at importam."""
        ...
