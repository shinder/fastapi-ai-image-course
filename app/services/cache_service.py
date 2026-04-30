"""Redis 快取服務（教材 6.4、6.5、6.6）"""
import hashlib
import json
import random
from typing import Annotated, Optional

import redis
from fastapi import Depends

from app.config import settings

# 連線池（執行緒安全，多請求共用）
_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


# 依賴注入別名
RedisDep = Annotated[redis.Redis, Depends(get_redis)]


def image_hash(content: bytes) -> str:
    """以圖片二進位內容做 SHA-256（教材 6.5）"""
    return hashlib.sha256(content).hexdigest()


def cache_get(r: redis.Redis, key: str) -> Optional[dict | list]:
    raw = r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set(r: redis.Redis, key: str, value: dict | list, ttl: int = 3600) -> None:
    r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)


def cache_set_jitter(
    r: redis.Redis,
    key: str,
    value: dict | list,
    base_ttl: int = 3600,
    jitter: float = 0.1,
) -> None:
    """TTL 加抖動（教材 6.6 防雪崩）"""
    ttl = int(base_ttl * (1 + random.uniform(-jitter, jitter)))
    r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)


# 教材 6.6 防穿透
SENTINEL = "__none__"


def cache_get_or_none(r: redis.Redis, key: str):
    raw = r.get(key)
    if raw == SENTINEL:
        return "miss-cached"
    return json.loads(raw) if raw else None
