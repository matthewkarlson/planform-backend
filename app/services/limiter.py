import os
import time
from upstash_redis import Redis # SDK for Upstash REST API
from fastapi.concurrency import run_in_threadpool

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", 100))
RATE_WINDOW    = int(os.getenv("RATE_WINDOW_SECONDS", 60 * 60))   # 1 hour in seconds

upstash_sdk_client = None

# Configuration for Upstash REST API SDK
REDIS_URL = os.getenv("REDIS_URL") # e.g., https://moved-oyster-22743.upstash.io
REDIS_TOKEN = os.getenv("REDIS_TOKEN")

if REDIS_URL and REDIS_TOKEN:
    try:
        upstash_sdk_client = Redis(
            url=REDIS_URL,
            token=REDIS_TOKEN
        )
        # Test connection by trying to get a non-existent key (or a known one)
        # The SDK doesn't have a direct .ping() like redis-py for REST.
        # A get command will verify token and URL.
        upstash_sdk_client.get("rate_limiter_ping_test") 
        print(f"Rate limiter connected to Upstash Redis via REST API at: {REDIS_URL}")
    except Exception as e:
        print(f"ERROR: Could not connect to Upstash Redis via REST API. Rate limiting may not work. Error: {e}")
        upstash_sdk_client = None
else:
    print("WARN: REDIS_URL or REDIS_TOKEN not set. Upstash SDK client not configured.")
    # Note: This version does not have a fallback to local Redis, as it's specifically for the Upstash SDK.
    # If you need local fallback, you'd re-introduce the redis-py client logic here or handle it upstream.

if not upstash_sdk_client:
    print("WARN: Upstash SDK client could not be configured for rate limiting. Limiter will allow all requests.")

def _perform_upstash_sdk_check(key_name: str):
    # This is a synchronous function using the Upstash SDK that will run in a thread pool
    global upstash_sdk_client
    if not upstash_sdk_client:
        raise ConnectionError("Upstash SDK client not initialized for _perform_upstash_sdk_check")

    # Upstash SDK pipeline for atomicity (if supported well for these commands, equivalent to MULTI/EXEC)
    # Note: The Upstash SDK's pipeline might behave differently than redis-py's. 
    # Check its documentation for atomicity guarantees for incr/expire combo.
    # For simplicity, let's do sequential calls; for strict atomicity, Upstash Lua might be needed via REST or a different approach.
    
    current_count = upstash_sdk_client.incr(key_name)
    if current_count == 1:
        # Set expiry only if the key is new (count is 1)
        upstash_sdk_client.expire(key_name, RATE_WINDOW)
    
    ttl = upstash_sdk_client.ttl(key_name)

    if ttl is None or ttl < 0: # ttl can be None if key doesn't exist or -1 for no expiry, -2 for no key
        # If key has no expiry (e.g., if incr happened but expire failed, or if key existed without TTL)
        # or if key somehow doesn't exist after incr (unlikely but defensive)
        # Ensure an expiry is set. This might re-set it if it already exists.
        upstash_sdk_client.expire(key_name, RATE_WINDOW)
        ttl = RATE_WINDOW # Assume it's set to the full window now
        
    return current_count, ttl

async def check(identifier: str):
    if not upstash_sdk_client:
        print(f"WARN: Upstash SDK client not available. Rate check for {identifier} allowed by default.")
        return {"allowed": True, "reset_at": time.time() + RATE_WINDOW, "current": 0, "limit": RATE_LIMIT_MAX}

    key = f"rate_limit:{identifier}"
    current_time = time.time()

    try:
        # Run the synchronous Upstash SDK operations in a separate thread
        current_count, ttl = await run_in_threadpool(_perform_upstash_sdk_check, key_name=key)
        
        is_allowed = current_count <= RATE_LIMIT_MAX
        reset_at = current_time + ttl

        return {
            "allowed": is_allowed,
            "reset_at": reset_at,
            "current": current_count,
            "limit": RATE_LIMIT_MAX,
        }
    except Exception as e:
        print(f"ERROR: Upstash SDK operation failed for rate limiting identifier {identifier}. Allowing request. Error: {e}")
        return {"allowed": True, "reset_at": current_time + RATE_WINDOW, "current": "unknown", "limit": RATE_LIMIT_MAX}
