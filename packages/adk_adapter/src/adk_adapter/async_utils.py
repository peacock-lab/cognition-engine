"""Async helpers for sync contract methods."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from threading import Thread
from typing import Any, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine from a sync API, even when a loop is already active."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: T | None = None
    error: BaseException | None = None

    def run_in_thread() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001
            error = exc

    thread = Thread(target=run_in_thread)
    thread.start()
    thread.join()
    if error is not None:
        raise error
    return result  # type: ignore[return-value]
