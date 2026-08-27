"""
Portas (contratos) de escrita — lado Command do CQRS.

Paralelo Zend:
  Interface que o ServiceManager resolveria
  (ex.: TransactionRepositoryInterface → TransactionRepository).
  O Use Case depende da interface, nunca da implementação MySQL.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.entities.transaction import Transaction


class TransactionRepositoryPort(Protocol):
    """Persistência transacional (INSERT/UPDATE). Sem SELECTs de relatório."""

    async def save(self, transaction: Transaction) -> Transaction:
        """Insere ou atualiza a entidade no armazenamento."""
        ...

    async def update_status(
        self,
        transaction_id: UUID,
        status: str,
    ) -> None:
        """Atualiza apenas o status (worker em background)."""
        ...
