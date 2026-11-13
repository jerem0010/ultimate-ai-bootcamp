
from redis.asyncio import Redis


RATE_LIMIT = 10
WINDOW_SECONDS = 60


RATE_LIMIT_SCRIPT = """
local count = redis.call("INCR", KEYS[1])

if count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

return {count, redis.call("TTL", KEYS[1])}
"""


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int = RATE_LIMIT,
    window: int = WINDOW_SECONDS,
) -> tuple[bool, int]:

    count, ttl = await redis.eval(
        RATE_LIMIT_SCRIPT,
        1,
        key,
        window,
    )

    allowed = count <= limit

    return allowed, ttl
