from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

import aio_pika

from glocal_service_kit.config import get_settings

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class RabbitMQ:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._lock = asyncio.Lock()

    async def _ensure_channel(self) -> aio_pika.abc.AbstractChannel:
        async with self._lock:
            if self._channel and not self._channel.is_closed:
                return self._channel
            self._connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=5)
            return self._channel

    async def declare_queue(self, name: str, routing_key: str, exchange: str = "jobs") -> None:
        channel = await self._ensure_channel()
        ex = await channel.declare_exchange(
            exchange,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        queue = await channel.declare_queue(name, durable=True)
        await queue.bind(ex, routing_key)

    async def consume(self, queue_name: str, handler: MessageHandler) -> None:
        channel = await self._ensure_channel()
        queue = await channel.declare_queue(queue_name, durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    payload = json.loads(message.body.decode("utf-8"))
                    await handler(payload)

    async def publish(
        self,
        routing_key: str,
        payload: dict[str, Any],
        exchange: str = "jobs",
    ) -> None:
        channel = await self._ensure_channel()
        ex = await channel.declare_exchange(exchange, aio_pika.ExchangeType.TOPIC, durable=True)
        await ex.publish(
            aio_pika.Message(body=json.dumps(payload).encode("utf-8")),
            routing_key=routing_key,
        )

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
        if self._connection is not None:
            await self._connection.close()
            self._connection = None


rabbitmq = RabbitMQ()
