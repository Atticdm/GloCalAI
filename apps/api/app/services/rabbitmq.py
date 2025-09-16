from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

import aio_pika

from app.core.config import settings

_connection_lock = asyncio.Lock()
_connection: aio_pika.RobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None


async def get_exchange() -> aio_pika.abc.AbstractExchange:
    global _connection, _channel, _exchange
    async with _connection_lock:
        if _exchange is not None:
            return _exchange
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _channel = await _connection.channel()
        await _channel.set_qos(prefetch_count=10)
        _exchange = await _channel.declare_exchange(
            "jobs",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        return _exchange


async def publish_event(routing_key: str, payload: Dict[str, Any]) -> None:
    exchange = await get_exchange()
    message = aio_pika.Message(body=json.dumps(payload).encode("utf-8"))
    await exchange.publish(message, routing_key=routing_key)


async def close_connection() -> None:
    global _connection, _channel, _exchange
    if _channel is not None:
        await _channel.close()
        _channel = None
    if _connection is not None:
        await _connection.close()
        _connection = None
    _exchange = None
