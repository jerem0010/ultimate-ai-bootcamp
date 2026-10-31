
import asyncio
import pytest


@pytest.mark.asyncio
async def test_semaphore_limit():
    semaphore = asyncio.Semaphore(2)

    active_requests = 0
    max_observed = 0

    async def fake_request():
        nonlocal active_requests, max_observed

        async with semaphore:
            active_requests += 1

            max_observed = max(
                max_observed,
                active_requests
            )

            try:
                await asyncio.sleep(0.1)
            finally:
                active_requests -= 1

    tasks = [
        asyncio.create_task(fake_request())
        for _ in range(10)
    ]

    await asyncio.gather(*tasks)

    assert max_observed == 2
    assert active_requests == 0
