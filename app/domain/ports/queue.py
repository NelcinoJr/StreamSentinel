"""
Porta da fila — publicação de eventos (ingestão assíncrona).

Paralelo Zend/PHP:
  Como enfileirar job no Beanstalkd/Gearman/RabbitMQ
  e responder ao cliente sem esperar o worker terminar.
"""

from __future__ import annotations

from typing import Any, Protocol


class EventPublisherPort(Protocol):
    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        """Publica mensagem na fila/stream (ex.: Redis)."""
        ...
