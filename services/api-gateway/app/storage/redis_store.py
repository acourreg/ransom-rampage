import json
from redis.asyncio import Redis

_redis: Redis | None = None

async def init_redis(url: str) -> None:
    """Initialize global Redis client on app startup."""
    global _redis
    _redis = Redis.from_url(url, decode_responses=True)
    try:
        await _redis.ping()
    except Exception as e:
        raise RuntimeError(f"Redis connection failed: {e}")

async def get_redis() -> Redis:
    """Get Redis client (for FastAPI Depends injection)."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis first.")
    return _redis

async def close_redis() -> None:
    """Close Redis client on app shutdown."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None

async def save_game(session_id: str, state: dict, ttl: int = 86400) -> None:
    """Save game state to Redis (JSON string)."""
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    key = f"game:{session_id}"
    await _redis.set(key, json.dumps(state), ex=ttl)

async def load_game(session_id: str) -> dict | None:
    """Load game state from Redis."""
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    key = f"game:{session_id}"
    data = await _redis.get(key)
    return json.loads(data) if data else None

async def delete_game(session_id: str) -> None:
    """Delete game state from Redis."""
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    key = f"game:{session_id}"
    await _redis.delete(key)
