"""Thin Gemini wrapper: retry with exponential backoff on 429 / RESOURCE_EXHAUSTED,
per-run request counter, model name from config."""
import random
import time
from typing import Callable, TypeVar

from . import config

T = TypeVar("T")


class BudgetExceeded(RuntimeError):
    pass


def is_rate_limit(exc: Exception) -> bool:
    return getattr(exc, "code", None) == 429 or "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)


class Counter:
    requests = 0


def with_backoff(fn: Callable[[], T], max_tries: int = 5, base: float = 2.0, sleep=time.sleep) -> T:
    for attempt in range(max_tries):
        if Counter.requests >= config.MAX_REQUESTS:
            raise BudgetExceeded(f"request cap {config.MAX_REQUESTS} reached for this run")
        Counter.requests += 1
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if not is_rate_limit(e) or attempt == max_tries - 1:
                raise
            sleep(base ** attempt + random.random())
    raise RuntimeError("unreachable")


_client = None


def client():
    global _client
    if _client is None:
        from google import genai
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY missing; copy .env.example to .env")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client
