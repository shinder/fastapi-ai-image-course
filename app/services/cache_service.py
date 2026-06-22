"""Redis 快取服務（教材 6.4、6.5、6.6、6.9）"""

import hashlib
import json
import random
from contextlib import contextmanager
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
    # 快取「盡力而為」：Redis 不可用時當作未命中（回 None），不讓呼叫端崩潰
    try:
        raw = r.get(key)
    except redis.RedisError:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set(r: redis.Redis, key: str, value: dict | list, ttl: int = 3600) -> None:
    # 寫快取失敗（Redis 不可用）不應影響主流程，直接略過
    try:
        r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
    except redis.RedisError:
        pass


def cache_incr(r: redis.Redis, key: str) -> None:
    """計數器 +1（如命中率統計）；Redis 不可用時略過。"""
    try:
        r.incr(key)
    except redis.RedisError:
        pass


def cache_set_jitter(
    r: redis.Redis,
    key: str,
    value: dict | list,
    base_ttl: int = 3600,
    jitter: float = 0.1,
) -> None:
    """TTL 加抖動（教材 6.6 防雪崩）"""
    ttl = int(base_ttl * (1 + random.uniform(-jitter, jitter)))
    try:
        r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
    except redis.RedisError:
        pass


# 教材 6.6 防穿透
SENTINEL = "__none__"


def cache_get_or_none(r: redis.Redis, key: str):
    # 與 cache_get 一致的盡力而為：Redis 不可用或內容非 JSON 時當作未命中
    try:
        raw = r.get(key)
    except redis.RedisError:
        return None
    if raw == SENTINEL:
        return "miss-cached"
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


@contextmanager
def acquire_lock(r: redis.Redis, key: str, ttl: int = 10):
    """分散式鎖（教材 6.9 防快取擊穿）。

    用 SET NX EX 嘗試取鎖：成功 yield True，已被別人持有 yield False。
    with 區塊結束會自動釋放（只有自己取得時才刪）。ttl 是保險，避免持鎖者
    當掉造成死鎖。Redis 不可用時採 fail-open（視為取得鎖，照常執行）。

    註：這是教學用的簡化版。正式環境若要嚴謹，釋放時應以「鎖的擁有者 token」
    比對後再刪（避免誤刪他人的鎖），可用 Lua 腳本原子完成。
    """
    acquired = True
    try:
        # nx=True：key 不存在才設定（等於「沒人持鎖才取得」）；ex=ttl：自動過期
        acquired = bool(r.set(key, "1", nx=True, ex=ttl))
    except redis.RedisError:
        acquired = True  # fail-open
    try:
        yield acquired
    finally:
        if acquired:
            try:
                r.delete(key)
            except redis.RedisError:
                pass
