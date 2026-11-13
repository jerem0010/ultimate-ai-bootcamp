
import pytest
from unittest.mock import AsyncMock, call

from app.retry import (
    retry,
    RetryableError,
    PermanentError,
)


@pytest.mark.asyncio
async def test_retry_immediate_success():
    """Une fonction qui réussit ne doit être appelée qu'une fois."""

    calls = 0

    async def func():
        nonlocal calls
        calls += 1
        return "success"

    result = await retry(func)

    assert result == "success"
    assert calls == 1


@pytest.mark.asyncio
async def test_retry_eventual_success():
    """Deux erreurs temporaires puis un succès."""

    calls = 0

    async def func():
        nonlocal calls
        calls += 1

        if calls < 3:
            raise RetryableError("Temporary failure")

        return "success"

    result = await retry(
        func,
        max_attempts=3,
        base_delay=0,
    )

    assert result == "success"
    assert calls == 3


@pytest.mark.asyncio
async def test_retry_exhausted():
    """Toutes les tentatives échouent."""

    calls = 0

    async def func():
        nonlocal calls
        calls += 1
        raise RetryableError("Provider unavailable")

    with pytest.raises(RetryableError):
        await retry(
            func,
            max_attempts=3,
            base_delay=0,
        )

    assert calls == 3


@pytest.mark.asyncio
async def test_permanent_error_no_retry():
    """Une erreur permanente ne doit jamais être retentée."""

    calls = 0

    async def func():
        nonlocal calls
        calls += 1
        raise PermanentError("Invalid API key")

    with pytest.raises(PermanentError):
        await retry(func, max_attempts=3)

    assert calls == 1


@pytest.mark.asyncio
async def test_invalid_max_attempts():
    """Une configuration invalide doit être rejetée."""

    async def func():
        return "success"

    with pytest.raises(ValueError):
        await retry(func, max_attempts=0)


@pytest.mark.asyncio
async def test_exponential_backoff(monkeypatch):
    """Vérifie les délais sans réellement attendre."""

    fake_sleep = AsyncMock()

    monkeypatch.setattr(
        "exercises.day_04.retry.asyncio.sleep",
        fake_sleep,
    )

    async def func():
        raise RetryableError("Temporary failure")

    with pytest.raises(RetryableError):
        await retry(
            func,
            max_attempts=4,
            base_delay=1,
            max_delay=30,
            jitter=False,
        )

    assert fake_sleep.await_args_list == [
        call(1),
        call(2),
        call(4),
    ]

@pytest.mark.asyncio
async def test_max_delay(monkeypatch):
    fake_sleep = AsyncMock()

    monkeypatch.setattr(
        "exercises.day_04.retry.asyncio.sleep",
        fake_sleep,
    )

    async def func():
        raise RetryableError("Temporary failure")

    with pytest.raises(RetryableError):
        await retry(
            func,
            max_attempts=6,
            base_delay=1,
            max_delay=3,
            jitter=False,
        )

    assert fake_sleep.await_args_list == [
        call(1),
        call(2),
        call(3),
        call(3),
        call(3),
    ]