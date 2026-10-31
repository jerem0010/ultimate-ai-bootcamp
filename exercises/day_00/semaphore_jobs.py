
import asyncio

async def process_job(job_id, semaphore):
    # TODO: acquire semaphore
    # TODO: print start
    # TODO: simulate 2 seconds of work
    # TODO: print completion
    # TODO: return job_id
    async with semaphore:
        print(f"start job n-{job_id}")
        await asyncio.sleep(2)
        print(f"job n {job_id} terminated")
        return job_id
    pass

async def main():
    semaphore = asyncio.Semaphore(2)

    # TODO: create 6 tasks
    tasks = [asyncio.create_task(process_job(i, semaphore)) for i in range(6)]

    # TODO: await all tasks
    results = await asyncio.gather(*tasks)

    # TODO: print results
    for result in results:
        print(result)
    pass

if __name__ == "__main__":
    asyncio.run(main())
