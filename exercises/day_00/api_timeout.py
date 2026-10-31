
import asyncio

async def call_model(model_name, duration):
    # TODO: simulate an API request
    await asyncio.sleep(duration)
    # TODO: return model_name
    return model_name

async def safe_call(model_name, duration):
    # TODO: use wait_for with a 2-second timeout
    try:
        result = await asyncio.wait_for(call_model(model_name, duration), timeout=2)
        return result
    # TODO: catch the timeout exception
    except asyncio.TimeoutError:
        # TODO: return a meaningful result
        return f"Timeout occurred while calling {model_name}"
    pass

async def main():
    # TODO: run GPT, Claude and Gemini concurrently
    results = await asyncio.gather(
        safe_call("GPT", 1),
        safe_call("Claude", 3),
        safe_call("Gemini", 2)
    )
    # TODO: display all results
    for result in results:
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
