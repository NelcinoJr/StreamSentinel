"""
Caso de uso de LEITURA — busca transação por ID.

Paralelo Zend:
  TransactionService::find($id) usando só SELECT (Finder),
  nunca TableGateway::insert.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.ports.finders import TransactionFinderPort


class GetTransactionUseCase:
    def __init__(self, finder: TransactionFinderPort) -> None:
        # Injeta a interface (ServiceManager), não o MySQL concreto
        self._finder = finder

    async def execute(self, transaction_id: UUID) -> dict[str, Any] | None:
        # None = não achou → Controller devolve 404
        return await self._finder.find_by_id(transaction_id)
