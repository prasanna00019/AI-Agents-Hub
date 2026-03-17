from __future__ import annotations

import asyncio
from typing import Any, Dict


_run_queues: Dict[str, asyncio.Queue] = {}


def get_run_queue(run_id: str) -> asyncio.Queue:
    if run_id not in _run_queues:
        _run_queues[run_id] = asyncio.Queue()
    return _run_queues[run_id]


def cleanup_run_queue(run_id: str) -> None:
    _run_queues.pop(run_id, None)


async def emit_run_event(run_id: str | None, event: Dict[str, Any]) -> None:
    if not run_id:
        return
    await get_run_queue(run_id).put(event)
