"""影像路由：CRUD、上傳、回傳檔案、上傳並辨識（綜合）

對應教材：
- 3.5 圖片上傳與儲存
- 3.6 圖片回傳（FileResponse、StreamingResponse、Base64）
- 4.6 CRUD
- 4.7 影像資料儲存策略
- 綜合實作：upload-and-classify
"""
import base64
import os
import uuid
from io import BytesIO
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image as PILImage
from sqlmodel import func, select

from app.config import settings
from app.database import SessionDep
from app.models.image import Image, ImageCreate, ImagePublic, ImageUpdate
from app.services.cache_service import RedisDep, cache_get, cache_set, image_hash

router = APIRouter(prefix="/api/v1/images", tags=["images"])

# 教材 3.5
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------- 4.6 CRUD ----------

@router.post("", response_model=ImagePublic, status_code=status.HTTP_201_CREATED)
def create_image(payload: ImageCreate, session: SessionDep):
    """純 JSON 建立（不含檔案）。檔案類欄位以佔位值補上，正式上傳請用 /upload"""
    image = Image.model_validate(
        payload,
        update={
            "filename": "placeholder.jpg",
            "file_path": "/tmp/placeholder.jpg",
            "file_size": 0,
            "mime_type": "image/jpeg",
        },
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


@router.get("", response_model=list[ImagePublic])
def list_images(
    session: SessionDep,
    skip: int = 0,
    limit: int = 20,
    keyword: str | None = None,
):
    statement = select(Image)
    if keyword:
        statement = statement.where(Image.title.contains(keyword))
    statement = statement.offset(skip).limit(limit).order_by(Image.uploaded_at.desc())
    return session.exec(statement).all()


@router.get("/stats/total")
def total_images(session: SessionDep):
    """計數查詢（教材 4.6）"""
    statement = select(func.count(Image.id))
    total = session.exec(statement).one()
    return {"total": total}


@router.get("/{image_id}", response_model=ImagePublic)
def get_image(image_id: int, session: SessionDep):
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(404, "找不到圖片")
    return image


@router.patch("/{image_id}", response_model=ImagePublic)
def update_image(image_id: int, payload: ImageUpdate, session: SessionDep):
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(404, "找不到圖片")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(image, key, value)
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: int, session: SessionDep):
    image = session.get(Image, image_id)
    if not image:
        raise HTTPException(404, "找不到圖片")
    session.delete(image)
    session.commit()


# ---------- 3.5 上傳 ----------

@router.post("/upload-only")
async def upload_image_only(file: UploadFile = File(...)):
    """單純上傳（不入庫，教材 3.5 範例）"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"不支援的格式：{file.content_type}")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "檔案過大（超過 10 MB）")

    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    new_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, new_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)

    return {
        "filename": new_name,
        "original_name": file.filename,
        "size": len(content),
        "content_type": file.content_type,
    }


@router.post("/upload-multi")
async def upload_multi(files: List[UploadFile] = File(...)):
    """多張同時上傳（教材 3.5）"""
    results = []
    for file in files:
        content = await file.read()
        results.append({"filename": file.filename, "size": len(content)})
    return {"count": len(results), "files": results}


@router.post("/upload-and-process")
async def upload_and_process(file: UploadFile = File(...)):
    """上傳並用 Pillow 處理（教材 3.5）"""
    content = await file.read()

    img = PILImage.open(BytesIO(content))
    info = {
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
    }

    img.thumbnail((800, 800))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    output = BytesIO()
    img.save(output, format="JPEG", quality=85, optimize=True)

    save_path = os.path.join(settings.UPLOAD_DIR, f"thumb_{uuid.uuid4().hex}.jpg")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(output.getvalue())

    return {
        "info": info,
        "thumbnail_size": len(output.getvalue()),
        "saved_to": save_path,
    }


# ---------- 4.7 上傳並入庫 ----------

@router.post("/upload", response_model=ImagePublic, status_code=201)
async def upload_image(
    session: SessionDep,
    title: str = Form(...),
    file: UploadFile = File(...),
):
    """上傳檔案並寫入資料庫（檔案進磁碟，路徑進 DB）"""
    content = await file.read()

    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    new_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, new_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    image = Image(
        title=title,
        filename=new_name,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


# ---------- 3.6 圖片回傳 ----------

@router.get("/{filename}/download")
def download_image(filename: str):
    """FileResponse（教材 3.6）"""
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "找不到檔案")
    return FileResponse(file_path, media_type="image/jpeg", filename=filename)


@router.get("/{filename}/stream")
def stream_image(filename: str):
    """串流回傳（教材 3.6）"""
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "找不到檔案")

    def iterfile():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(iterfile(), media_type="image/jpeg")


@router.get("/{filename}/base64")
def image_base64(filename: str):
    """Base64 回傳（教材 3.6，小圖適用）"""
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "找不到檔案")
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return {"filename": filename, "data": f"data:image/jpeg;base64,{encoded}"}


# ---------- 綜合實作：上傳 + 辨識 + 快取 + 入庫 ----------

@router.post("/upload-and-classify", response_model=ImagePublic, status_code=201)
async def upload_and_classify(
    session: SessionDep,
    r: RedisDep,
    title: str = Form(...),
    file: UploadFile = File(...),
):
    """完整流程（綜合實作專案）：

    1. 圖片 hash 查 Redis
    2. 未命中 → 呼叫本地 AI 模型
    3. 寫 Redis 與 PostgreSQL
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "請上傳圖片")

    content = await file.read()
    digest = image_hash(content)

    # 1. 查快取
    cache_key = f"cache:ai:classify:{digest}"
    ai_result = cache_get(r, cache_key)
    cache_hit = ai_result is not None

    # 2. 未命中 → AI 推論（需 uv sync --extra ml）
    if not cache_hit:
        from app.services.ai_service import classify_image_bytes

        ai_result = await run_in_threadpool(classify_image_bytes, content)
        cache_set(r, cache_key, ai_result, ttl=86400)  # 24 小時

    # 3. 儲存圖片（以 hash 命名，避免重複儲存）
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    new_name = f"{digest}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, new_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(content)

    # 4. 寫入資料庫
    image = Image(
        title=title,
        filename=new_name,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        ai_result={"results": ai_result, "from_cache": cache_hit},
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image
