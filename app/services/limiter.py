import os
import time
import redis.asyncio as aioredis # Use the async library

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", 100))
RATE_WINDOW    = int(os.getenv("RATE_WINDOW_SECONDS", 60 * 60))   # 1 hour in seconds

# Determine Redis URL:
# 1. Try UPSTASH_REDIS_URL (for production, often starts with rediss:// for SSL)
# 2. Fallback to REDIS_URL (for local Docker redis, e.g., redis://redis:6379 or redis://localhost:6379)
# 3. Default if neither is set (primarily for docker-compose context where service is named 'redis')
FINAL_REDIS_URL = os.getenv("UPSTASH_REDIS_URL") or \
                  os.getenv("REDIS_URL", "redis://redis:6379")

redis_client = None
if FINAL_REDIS_URL:
    try:
        redis_client = aioredis.from_url(FINAL_REDIS_URL)
        print(f"Rate limiter connected to Redis at: {FINAL_REDIS_URL}")
    except Exception as e:
        print(f"ERROR: Could not connect to Redis at {FINAL_REDIS_URL}. Rate limiting may not work. Error: {e}")
else:
    print("WARN: No REDIS_URL or UPSTASH_REDIS_URL provided. Rate limiting will not connect to Redis.")

async def check(identifier: str):
    if not redis_client:
        print(f"WARN: Redis client not available. Rate check for {identifier} allowed by default.")
        return {"allowed": True, "reset_at": time.time() + RATE_WINDOW, "current": 0, "limit": RATE_LIMIT_MAX}

    key = f"rate_limit:{identifier}" # Changed key prefix for clarity
    current_time = time.time()

    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            # Increment the count for the current window
            pipe.incr(key)
            # Set expiry only if the key is new (count is 1)
            # This is an atomic way to set TTL on first increment
            pipe.expire(key, RATE_WINDOW, nx=True) # nx=True sets expiry only if no expiry is already set
            # Get the current count and TTL after operations
            pipe.ttl(key)
            results = await pipe.execute()
        
        current_count = results[0]
        ttl = results[2] # TTL is the third command in the pipeline

        if ttl == -2: # Key does not exist (shouldn't happen if incr worked, but good check)
            ttl = RATE_WINDOW
        elif ttl == -1: # Key exists but has no associated expire
            # This can happen if expire(nx=True) didn't set because key already had TTL or an issue occurred.
            # To be safe, re-apply expire, or assume RATE_WINDOW.
            await redis_client.expire(key, RATE_WINDOW)
            ttl = RATE_WINDOW

        is_allowed = current_count <= RATE_LIMIT_MAX
        reset_at = current_time + ttl

        return {
            "allowed": is_allowed,
            "reset_at": reset_at,
            "current": current_count,
            "limit": RATE_LIMIT_MAX,
        }
    except Exception as e:
        print(f"ERROR: Redis operation failed for rate limiting identifier {identifier}. Allowing request. Error: {e}")
        # Fallback: allow the request if Redis fails to prevent blocking users due to limiter issues.
        return {"allowed": True, "reset_at": current_time + RATE_WINDOW, "current": "unknown", "limit": RATE_LIMIT_MAX}
