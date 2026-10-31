
import asyncio

async def process_job(job_id, duration):
    # TODO: print start
    print(f"start job n-{job_id}")
    # TODO: simulate processing
    await asyncio.sleep(duration)
    # TODO: print completion
    print(f"job n {job_id} terminated")
    # TODO: return job_id
    return (job_id)
    pass

async def main():
    # TODO: create three tasks with create_task()
    task1 = asyncio.create_task(process_job("1", 2))
    task2 = asyncio.create_task(process_job("2", 7))
    task3 = asyncio.create_task(process_job("3", 3))

    print("All jobs scheduled")

    # TODO: await the tasks and collect results
    result1 = await task1
    result2 = await task2
    result3 = await task3

    # TODO: print results
    print(result1)
    print(result2)
    print(result3)

    pass

if __name__ == "__main__":
    asyncio.run(main())
