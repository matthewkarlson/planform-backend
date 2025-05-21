import os, time
import redis
RATE_LIMIT_MAX = 100
RATE_WINDOW    = 60 * 60   # 1 h

REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")

r = redis.Redis(
  host=REDIS_URL,
  port=6379,
  password=REDIS_TOKEN,
  ssl=True
)

async def check(identifier: str):
    key      = f"rate:{identifier}"
    current  = await r.incr(key)
    if current == 1:
        await r.expire(key, RATE_WINDOW)
    ttl = await r.ttl(key)
    return {
        "allowed": current <= RATE_LIMIT_MAX,
        "reset_at": time.time() + ttl,
        "current": current,
        "limit": RATE_LIMIT_MAX,
    }
