"""RQ 任務函式（教材 7.11 方法二）

寫成一般函式，RQ worker 會在它自己的行程裡呼叫它。
啟動 worker（用 RQ 內建指令，不必自己寫迴圈）：

    rq worker image-gen --url redis://localhost:6379/0
"""

from app.services.cache_service import cache_set, get_redis
from app.services.image_gen_service import generate_image


def run_generation(task_id: str, prompt: str) -> str:
    """RQ worker 會呼叫這個函式；拋出例外時 RQ 會記到 failed 佇列。"""
    r = get_redis()
    task_key = f"task:gen:{task_id}"
    cache_set(r, task_key, {"status": "running"}, ttl=3600)
    url = generate_image(prompt)
    cache_set(r, task_key, {"status": "done", "url": url}, ttl=3600)
    return url
