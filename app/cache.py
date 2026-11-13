
import hashlib
import json

from redis.asyncio import Redis


CACHE_TTL = 3600


def build_cache_key(
    model: str,
    prompt: str,
    max_tokens: int,
) -> str:
    # Sérialisation déterministe des paramètres.
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
    )

    # Génération d'une clé unique de longueur fixe.
    digest = hashlib.sha256(
        payload.encode()
    ).hexdigest()

    return f"ai:cache:v1:{digest}"


async def get_cached_response(
    redis: Redis,
    key: str,
) -> str | None:
    return await redis.get(key)


async def cache_response(
    redis: Redis,
    key: str,
    response: str,
    ttl: int = CACHE_TTL,
) -> None:
    await redis.set(
        key,
        response,
        ex=ttl,
    )
