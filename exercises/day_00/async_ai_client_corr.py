
import asyncio

TIMEOUT = 2
MAX_ATTEMPTS = 3
MAX_CONCURRENT = 2


async def simulate_api(model: str, duration: float, attempt: int) -> str:
    print(f"[{model}] Attempt {attempt} started")

    await asyncio.sleep(duration)

    if model == "Llama" and attempt == 1:
        raise ConnectionError(f"{model} temporarily unavailable")

    print(f"[{model}] Attempt {attempt} succeeded")
    return model


async def call_with_retry(model: str, duration: float) -> str:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await asyncio.wait_for(
                simulate_api(model, duration, attempt),
                timeout=TIMEOUT,
            )
            return result

        except (ConnectionError, TimeoutError) as error:
            print(f"[{model}] Attempt {attempt} failed: {error}")

            if attempt == MAX_ATTEMPTS:
                raise

            delay = 2 ** (attempt - 1)
            print(f"[{model}] Retrying in {delay}s...")
            await asyncio.sleep(delay)

    raise RuntimeError("Unreachable")


async def limited_call(
    model: str,
    duration: float,
    semaphore: asyncio.Semaphore,
) -> str:
    async with semaphore:
        try:
            return await call_with_retry(model, duration)

        except (ConnectionError, TimeoutError) as error:
            return f"{model}: FAILED ({type(error).__name__})"


async def main() -> None:
    models = [
        ("GPT", 1),
        ("Claude", 3),
        ("Gemini", 0.5),
        ("Llama", 0.5),
        ("Mistral", 1),
    ]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = [
        asyncio.create_task(
            limited_call(model, duration, semaphore),
            name=f"request-{model}",
        )
        for model, duration in models
    ]

    results = await asyncio.gather(*tasks)

    print("\n=== FINAL RESULTS ===")
    for model, result in zip(models, results):
        print(f"{model[0]}: {result}")


if __name__ == "__main__":
    asyncio.run(main())
