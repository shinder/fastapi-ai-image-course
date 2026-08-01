"""AI 路由：Ollama 描述、分類、OCR、影像生成、外部 API

對應教材：
- 8.4 在 FastAPI 中呼叫 Ollama 視覺模型（含 run_in_threadpool）
- 8.5 用檔案雜湊快取辨識結果（記憶體 dict 版）
- 8.6 雲端模型與 OpenAI 相容介面
- 7.4 串接外部公開 API
- 附錄 E 換成 Redis 的快取與命中率統計
- 附錄 D 影像分類、OCR、影像生成
"""

import os
import time
from uuid import uuid4

import redis
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.database import SessionDep
from app.models.image import Image
from app.services.cache_service import (
    RedisDep,
    cache_get,
    cache_incr,
    cache_set,
    get_redis,
    image_hash,
)
from app.services.rate_limit import RateLimit

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


# ---------- 6.3 + 7.5 影像分類（含快取） ----------


@router.post("/classify", dependencies=[Depends(RateLimit(limit=30, window=60))])
async def classify(file: UploadFile = File(...), r: RedisDep = None):
    """以圖片 hash 為快取 key，未命中才呼叫模型，並統計命中率（教材 附錄 E）"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "請上傳圖片")

    content = await file.read()
    digest = image_hash(content)
    key = f"cache:ai:classify:{digest}"

    # 1. 先查快取（Redis 不可用時 cache_get 會回 None，視為未命中）
    cached = cache_get(r, key)
    if cached is not None:
        cache_incr(r, "stats:cache:hit")
        return {"results": cached, "cached": True}

    # 2. 未命中：執行推論（教材 8.4 thread pool 不阻塞事件迴圈）
    from app.services.ai_service import classify_image_bytes  # lazy import

    results = await run_in_threadpool(classify_image_bytes, content)

    # 3. 寫回快取（1 小時過期；Redis 不可用時自動略過，不影響回應）
    cache_set(r, key, results, ttl=3600)
    cache_incr(r, "stats:cache:miss")

    return {"results": results, "cached": False}


# ---------- 6.4 OCR ----------


@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "請上傳圖片")
    from app.services.ocr_service import extract_text  # lazy import

    content = await file.read()
    # 計時：只量 AI 推論本身（OCR 第一次會載入模型，會明顯比後續請求慢）
    start = time.perf_counter()
    results = await run_in_threadpool(extract_text, content)
    elapsed_seconds = round(time.perf_counter() - start, 2)
    full_text = "\n".join(r["text"] for r in results)
    return {"full_text": full_text, "details": results, "elapsed_seconds": elapsed_seconds}


# ---------- 6.5 Ollama 視覺模型 ----------


@router.post("/describe")
async def describe(
    file: UploadFile = File(...),
    prompt: str = Form("請以繁體中文描述這張圖片"),
):
    """用本機 Ollama 視覺模型描述圖片"""
    from app.services.ollama_service import describe_image  # lazy import

    content = await file.read()
    # 計時：只量 Ollama 推論本身（描述任務通常數秒，視模型與硬體而定）
    start = time.perf_counter()
    description = await run_in_threadpool(describe_image, content, prompt)
    elapsed_seconds = round(time.perf_counter() - start, 2)
    return {
        "model": settings.OLLAMA_VISION_MODEL,
        "description": description,
        "elapsed_seconds": elapsed_seconds,
    }


# ---------- 8.5 用檔案雜湊快取辨識結果（記憶體 dict 版）----------


@router.post("/describe-cached")
async def describe_cached(
    file: UploadFile = File(...),
    prompt: str = Form("請以繁體中文描述這張圖片"),
):
    """與 /describe 相同，但先查快取（教材 8.5）。

    同一張圖第二次呼叫會直接回傳上次的結果，elapsed_seconds 幾乎是 0。
    快取 key 用的是「圖片內容的 sha256」，所以換個檔名重傳一樣會命中。
    """
    from app.services import memo_cache
    from app.services.ollama_service import describe_image  # lazy import

    content = await file.read()
    key = memo_cache.image_key(content, "describe")

    # 1. 先查快取
    cached = memo_cache.get(key)
    if cached is not None:
        return {**cached, "cached": True, "elapsed_seconds": 0.0}

    # 2. 未命中才真的跑模型
    start = time.perf_counter()
    description = await run_in_threadpool(describe_image, content, prompt)
    elapsed_seconds = round(time.perf_counter() - start, 2)

    # 3. 把結果寫回快取，下次就不必再算
    result = {"model": settings.OLLAMA_VISION_MODEL, "description": description}
    memo_cache.set(key, result)
    return {**result, "cached": False, "elapsed_seconds": elapsed_seconds}


@router.get("/describe-cached/stats")
def describe_cache_stats():
    """記憶體快取的命中率統計（教材 8.5）。

    對照 /cache/stats——那是 Redis 版（教材 附錄 E）。
    """
    from app.services import memo_cache

    return memo_cache.stats()


@router.post("/extract-invoice")
async def extract_invoice(file: UploadFile = File(...)):
    """從發票圖片抽取結構化資訊（教材 8.4）"""
    from app.services.ollama_service import extract_invoice_info  # lazy import

    content = await file.read()
    data = await run_in_threadpool(extract_invoice_info, content)
    return data


# ---------- 6.6 影像生成 ----------


@router.post("/generate", dependencies=[Depends(RateLimit(limit=10, window=60))])
def generate(prompt: str = Form(..., min_length=1, max_length=1000)):
    """OpenAI gpt-image-1 影像生成（教材 附錄 D）"""
    from app.services.image_gen_service import generate_image  # lazy import

    url = generate_image(prompt)
    return {"prompt": prompt, "image_url": url}


# 任務狀態存 Redis（教材 附錄 E）：取代記憶體 dict，可跨 worker、可設 TTL 自動清理
def _task_key(task_id: str) -> str:
    return f"task:gen:{task_id}"


def _run_generation(task_id: str, prompt: str):
    """背景執行：產生圖片並把狀態寫進 Redis（用 get_redis 取得 client）"""
    from app.services.image_gen_service import generate_image

    r = get_redis()
    cache_set(r, _task_key(task_id), {"status": "running"}, ttl=3600)
    try:
        url = generate_image(prompt)
        cache_set(r, _task_key(task_id), {"status": "done", "url": url}, ttl=3600)
    except Exception as e:
        cache_set(r, _task_key(task_id), {"status": "error", "error": str(e)}, ttl=3600)


@router.post("/generate-async")
def generate_async(
    background_tasks: BackgroundTasks,
    r: RedisDep,
    prompt: str = Form(..., min_length=1),
):
    task_id = uuid4().hex
    cache_set(r, _task_key(task_id), {"status": "pending"}, ttl=3600)  # 先標記 pending
    background_tasks.add_task(_run_generation, task_id, prompt)  # 回應後才執行
    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, r: RedisDep):
    # 從 Redis 讀任務狀態；找不到（或已過期）回 not_found
    return cache_get(r, _task_key(task_id)) or {"status": "not_found"}


# ---------- 7.4 / 附錄 C 串接外部公開 API ----------


@router.post("/import-random")
async def import_random(session: SessionDep):
    """從公開圖庫（Lorem Picsum）抓一張圖，存檔並寫進資料庫（教材 7.4）。

    requests 是同步的，一定要丟到 thread pool——否則那 15 秒的逾時期間，
    整個服務一個請求都處理不了。
    """
    from app.services.external_ai import fetch_random_image

    try:
        content, filename = await run_in_threadpool(fetch_random_image)
    except RuntimeError as exc:
        # 外部服務出問題屬於「上游壞了」，回 502 比 500 精確
        raise HTTPException(502, str(exc))

    new_name = f"{uuid4().hex}.jpg"
    file_path = os.path.join(settings.UPLOAD_DIR, new_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    image = Image(
        title=f"picsum：{filename}",
        filename=new_name,
        file_path=file_path,
        file_size=len(content),
        mime_type="image/jpeg",
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return {"id": image.id, "filename": new_name, "size": len(content)}


@router.get("/fetch-many")
async def fetch_many(count: int = 3):
    """並行抓多張圖，比較 asyncio.gather 與逐一抓的差別（教材 附錄 C）。"""
    from app.services.external_ai import fetch_many_async

    sizes = await fetch_many_async(count)
    return {"count": len(sizes), "sizes": sizes}


# ---------- 附錄 E 命中率查詢 ----------


@router.get("/cache/stats")
def cache_stats(r: RedisDep):
    # Redis 不可用時回報 available=False，而非讓端點 500
    try:
        hit = int(r.get("stats:cache:hit") or 0)
        miss = int(r.get("stats:cache:miss") or 0)
    except redis.RedisError:
        return {"available": False, "hit": 0, "miss": 0, "total": 0, "hit_rate": 0}
    total = hit + miss
    return {
        "available": True,
        "hit": hit,
        "miss": miss,
        "total": total,
        "hit_rate": round(hit / total, 4) if total else 0,
    }


@router.get("/cache-test")
def cache_test(r: RedisDep):
    """教材 附錄 E 依賴注入示範。

    這裡刻意直接呼叫 r.set()/r.get()（不經 cache_service 的 helper），
    所以要自己處理 Redis 不可用的情況：回 503 而不是讓例外冒出去變成 500。
    注意 RedisDep 取得 client 時不會真的連線（redis-py 是惰性連線），
    要等下面實際下指令才會發現連不上，因此 try 要包住指令本身。
    """
    try:
        r.set("hello", "world", ex=60)
        return {"value": r.get("hello")}
    except redis.RedisError as exc:
        raise HTTPException(503, f"Redis 連線失敗，請確認 Redis 是否啟動：{exc}")
