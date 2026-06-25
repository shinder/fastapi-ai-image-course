"""速率限制（教材 7.8）：用 Redis INCR + EXPIRE 限制呼叫頻率。

做成 FastAPI 依賴，套在昂貴的 AI 端點上，保護後端不被爆量呼叫。
Redis 不可用時採 fail-open（放行），不讓限流元件本身成為單點故障。
"""

import redis
from fastapi import HTTPException, Request

from app.services.cache_service import RedisDep


class RateLimit:
    """每個來源在 window 秒內最多 limit 次。

    用法：
        @router.post(..., dependencies=[Depends(RateLimit(limit=30, window=60))])
    """

    def __init__(self, limit: int = 30, window: int = 60):
        self.limit = limit
        self.window = window

    def __call__(self, request: Request, r: RedisDep) -> None:
        # 以用戶端 IP 當識別；正式環境可改用 API Key（見教材 7.8 變體）
        client = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client}"
        try:
            count = r.incr(key)  # 計數 +1（key 不存在會從 1 開始）
            if count == 1:
                r.expire(key, self.window)  # 第一次才設過期，形成固定時間視窗
        except redis.RedisError:
            return  # fail-open：Redis 不可用時直接放行

        if count > self.limit:
            raise HTTPException(
                status_code=429,  # Too Many Requests
                detail=f"請求過於頻繁，每 {self.window} 秒上限 {self.limit} 次",
            )
