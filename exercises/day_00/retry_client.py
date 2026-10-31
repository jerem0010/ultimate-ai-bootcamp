
import asyncio


async def unreliable_api(attempt):
    print(f"Attempt {attempt}")

    if attempt <= 2:
        raise ConnectionError("API call failed")

    return "Success"


async def retry_request(max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        try:
            result = await unreliable_api(attempt)
            return result

        except ConnectionError as e:
            print(f"Attempt {attempt} failed: {e}")

            if attempt == max_attempts:
                raise

            delay = 2 ** (attempt - 1)
            print(f"Retrying in {delay}s...")
            await asyncio.sleep(delay)


async def main():
    result = await retry_request()
    print("Final result:", result)


if __name__ == "__main__":
    asyncio.run(main())
