"""
Adapter Redis — publica eventos na fila.

Paralelo Zend/PHP:
  Cliente Beanstalkd/RabbitMQ encapsulado atrás de uma interface.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


class RedisEventPublisher:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        await self._redis.rpush(channel, json.dumps(payload, default=str))
