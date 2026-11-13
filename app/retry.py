
import asyncio
import random
from collections.abc import Awaitable, Callable


class RetryableError(Exception):
    pass


class PermanentError(Exception):
    pass


async def retry(
    func: Callable[[], Awaitable],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
):
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    if base_delay < 0 or max_delay < 0:
        raise ValueError("Delays must be >= 0")

    for attempt in range(max_attempts):
        try:
            return await func()

        except RetryableError as exc:

            # Dernière tentative : on abandonne.
            if attempt == max_attempts - 1:
                raise

            # Exponential backoff avec plafond.
            delay = min(
                base_delay * 2 ** attempt,
                max_delay,
            )

            # Full Jitter.
            if jitter:
                delay = random.uniform(0, delay)

            print(
                f"Attempt {attempt + 1} failed: {exc}. "
                f"Retrying in {delay:.2f}s"
            )

            await asyncio.sleep(delay)
