
import asyncio

TIMEOUT = 2
MAX_ATTEMPTS = 3
MAX_CONCURRENT = 2


async def simulate_api(model, duration, attempt):
    # TODO: print model and attempt
    print(f"Calling {model} (attempt {attempt})")
    # TODO: simulate delay
    await asyncio.sleep(duration)
    # TODO: Llama fails on its first attempt
    if model == "Llama" and attempt == 1:
        raise ConnectionError("Llama API call failed")
    # TODO: return model name
    return model

async def call_with_retry(model, duration):
    # TODO: loop over attempts
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await asyncio.wait_for(simulate_api(model, duration, attempt), timeout=TIMEOUT)
            return result
        except (ConnectionError, asyncio.TimeoutError) as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt == MAX_ATTEMPTS:
                raise
            delay = 2 ** (attempt - 1)
            print(f"Retrying in {delay}s...")
            await asyncio.sleep(delay)
    # TODO: call simulate_api using wait_for
    # TODO: catch ConnectionError and TimeoutError
    # TODO: exponential backoff
    # TODO: propagate final failure
    raise RuntimeError("All attempts failed")
    pass


async def limited_call(model, duration, semaphore):
    # TODO: acquire semaphore
    async with semaphore:
        try:
            result = await call_with_retry(model, duration)
            return result
        except Exception as e:
            return f"Failed to call {model}: {e}"
    # TODO: call_with_retry

    # TODO: convert final failure into a result
    return f"Failed to call {model}: {e}"
    pass


async def main():
    models = [
        ("GPT", 1),
        ("Claude", 3),
        ("Gemini", 0.5),
        ("Llama", 0.5),
        ("Mistral", 1),
    ]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # TODO: create all tasks
    tasks = [limited_call(model, duration, semaphore) for model, duration in models]
    # TODO: await all results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # TODO: display results
    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
