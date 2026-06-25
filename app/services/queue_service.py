"""任務佇列（教材 7.11）

提供兩種做法：
- 方法一：用 Redis List（LPUSH/BRPOP）手刻最小佇列，零額外依賴、用來理解原理。
- 方法二：用 RQ（Redis Queue），內建重試、逾時、失敗追蹤，適合正式專案。
  需安裝可選依賴：uv sync --extra queue
"""

import json

from redis import Redis
from rq import Queue

from app.config import settings
from app.services.cache_service import get_redis

# ---------- 方法一：用 Redis List 手刻最小佇列 ----------

QUEUE_KEY = "queue:image-gen"


def enqueue_generation(task_id: str, prompt: str) -> None:
    """把任務 LPUSH 進佇列（左進）；worker 從右端 BRPOP 取出（先進先出）"""
    r = get_redis()
    job = {"task_id": task_id, "prompt": prompt}
    r.lpush(QUEUE_KEY, json.dumps(job, ensure_ascii=False))


# ---------- 方法二：用 RQ（Redis Queue）----------

# 注意：RQ 需要 bytes 回應，要用「未設 decode_responses」的獨立 client，
# 不能共用 7.4 那個 decode_responses=True 的連線池。
# Redis.from_url / Queue() 都是延遲連線，import 時不會真的連到 Redis。
_rq_redis = Redis.from_url(settings.REDIS_URL)
task_queue = Queue("image-gen", connection=_rq_redis)
