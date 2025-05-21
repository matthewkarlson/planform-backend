import os, time
import redis.asyncio as aioredis
RATE_LIMIT_MAX = 100
RATE_WINDOW    = 60 * 60   # 1 h

redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))

async def check(identifier: str):
    key      = f"rate:{identifier}"
    current  = await redis.incr(key)
    if current == 1:
        await redis.expire(key, RATE_WINDOW)
    ttl = await redis.ttl(key)
    return {
        "allowed": current <= RATE_LIMIT_MAX,
        "reset_at": time.time() + ttl,
        "current": current,
        "limit": RATE_LIMIT_MAX,
    }
