"""AI 路由：分類、OCR、Ollama 描述、影像生成、外部 API

對應教材：
- 5.3 影像分類（含 Redis 快取）
- 5.4 OCR
- 5.5 Ollama 視覺模型
- 5.6 影像生成（OpenAI DALL·E、含背景任務）
- 5.7 run_in_threadpool
- 6.5 快取 AI 推論結果（含命中率統計）
- 7.5 串接外部 AI API
"""
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.services.cache_service import RedisDep, cache_get, cache_set, image_hash

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


# ---------- 5.3 + 6.5 影像分類（含快取） ----------

@router.post("/classify")
async def classify(file: UploadFile = File(...), r: RedisDep = None):
    """以圖片 hash 為快取 key，未命中才呼叫模型，並統計命中率（教材 6.5、6.7）"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "請上傳圖片")

    content = await file.read()
    digest = image_hash(content)
    key = f"cache:ai:classify:{digest}"

    # 1. 先查快取
    cached = cache_get(r, key)
    if cached is not None:
        r.incr("stats:cache:hit")
        return {"results": cached, "cached": True}

    # 2. 未命中：執行推論（教材 5.7 thread pool 不阻塞事件循環）
    from app.services.ai_service import classify_image_bytes  # lazy import

    results = await run_in_threadpool(classify_image_bytes, content)

    # 3. 寫回快取（1 小時過期）
    cache_set(r, key, results, ttl=3600)
    r.incr("stats:cache:miss")

    return {"results": results, "cached": False}


# ---------- 5.4 OCR ----------

@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "請上傳圖片")
    from app.services.ocr_service import extract_text  # lazy import

    content = await file.read()
    results = await run_in_threadpool(extract_text, content)
    full_text = "\n".join(r["text"] for r in results)
    return {"full_text": full_text, "details": results}


# ---------- 5.5 Ollama 視覺模型 ----------

@router.post("/describe")
async def describe(
    file: UploadFile = File(...),
    prompt: str = Form("請以繁體中文描述這張圖片"),
):
    """用本地 Ollama 視覺模型描述圖片"""
    from app.services.ollama_service import describe_image  # lazy import

    content = await file.read()
    description = await run_in_threadpool(describe_image, content, prompt)
    return {
        "model": settings.OLLAMA_VISION_MODEL,
        "description": description,
    }


@router.post("/extract-invoice")
async def extract_invoice(file: UploadFile = File(...)):
    """從發票圖片抽取結構化資訊（教材 5.5）"""
    from app.services.ollama_service import extract_invoice_info  # lazy import

    content = await file.read()
    data = await run_in_threadpool(extract_invoice_info, content)
    return data


# ---------- 5.6 影像生成 ----------

@router.post("/generate")
def generate(prompt: str = Form(..., min_length=1, max_length=1000)):
    """OpenAI DALL·E 影像生成（教材 5.6）"""
    from app.services.image_gen_service import generate_image  # lazy import

    url = generate_image(prompt)
    return {"prompt": prompt, "image_url": url}


# 簡易任務佇列（教材 5.6 BackgroundTasks）
tasks: dict[str, dict] = {}


def _run_generation(task_id: str, prompt: str):
    from app.services.image_gen_service import generate_image

    tasks[task_id] = {"status": "running"}
    try:
        url = generate_image(prompt)
        tasks[task_id] = {"status": "done", "url": url}
    except Exception as e:
        tasks[task_id] = {"status": "error", "error": str(e)}


@router.post("/generate-async")
def generate_async(
    background_tasks: BackgroundTasks,
    prompt: str = Form(..., min_length=1),
):
    task_id = uuid4().hex
    tasks[task_id] = {"status": "pending"}
    background_tasks.add_task(_run_generation, task_id, prompt)
    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    return tasks.get(task_id, {"status": "not_found"})


# ---------- 7.5 / 7.6 串接外部 AI API ----------

@router.post("/classify-external")
async def classify_external(file: UploadFile = File(...)):
    """同步 requests + run_in_threadpool（教材 7.5）"""
    from app.services.external_ai import call_external_classify

    content = await file.read()
    result = await run_in_threadpool(call_external_classify, content)
    return result


@router.post("/classify-external-async")
async def classify_external_async(file: UploadFile = File(...)):
    """非同步 httpx（教材 7.6）"""
    from app.services.external_ai import call_external_classify_async

    content = await file.read()
    result = await call_external_classify_async(content)
    return result


# ---------- 6.7 命中率查詢 ----------

@router.get("/cache/stats")
def cache_stats(r: RedisDep):
    hit = int(r.get("stats:cache:hit") or 0)
    miss = int(r.get("stats:cache:miss") or 0)
    total = hit + miss
    return {
        "hit": hit,
        "miss": miss,
        "total": total,
        "hit_rate": round(hit / total, 4) if total else 0,
    }


@router.get("/cache-test")
def cache_test(r: RedisDep):
    """教材 6.4 依賴注入示範"""
    r.set("hello", "world", ex=60)
    return {"value": r.get("hello")}
