"""
Caso de uso de LEITURA — lista por período (relatório).

Paralelo Zend:
  Relatório / Query Object: só SELECT com filtro de datas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.ports.finders import TransactionFinderPort


class ListTransactionsUseCase:
    def __init__(self, finder: TransactionFinderPort) -> None:
        self._finder = finder

    async def execute(
        self,
        started_at: datetime,
        ended_at: datetime,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self._finder.list_by_period(
            started_at=started_at,
            ended_at=ended_at,
            limit=limit,
            offset=offset,
        )
