"""手刻佇列 worker（教材 6.11 方法一）

與 API 不同的獨立程式進入點，負責消費 Redis 佇列裡的任務。
啟動（可開多個平行消費同一個佇列）：

    python -m app.workers.queue_worker
"""
import json

from app.services.cache_service import cache_set, get_redis
from app.services.image_gen_service import generate_image
from app.services.queue_service import QUEUE_KEY


def main():
    r = get_redis()
    print("worker 啟動，等待任務…")
    while True:
        # brpop 阻塞等待，回傳 (key, value)；沒任務時不空轉吃 CPU
        _, raw = r.brpop(QUEUE_KEY)
        job = json.loads(raw)
        task_id, prompt = job["task_id"], job["prompt"]
        task_key = f"task:gen:{task_id}"
        cache_set(r, task_key, {"status": "running"}, ttl=3600)
        try:
            url = generate_image(prompt)
            cache_set(r, task_key, {"status": "done", "url": url}, ttl=3600)
        except Exception as e:
            cache_set(r, task_key, {"status": "error", "error": str(e)}, ttl=3600)


if __name__ == "__main__":
    main()
