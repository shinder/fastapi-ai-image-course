"""影像路由：CRUD、上傳、回傳檔案、上傳並辨識（綜合）

對應教材：
- 3.5 圖片上傳與儲存
- 3.6 圖片回傳（FileResponse、StreamingResponse、Base64）
- 4.6 CRUD
- 4.7 影像資料儲存策略
- 綜合實作：upload-and-classify
"""

import base64
import mimetypes
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

# 教材 3.5：上傳檔案的共用驗證條件
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}  # MIME 類型白名單，擋掉非圖片
MAX_SIZE = 10 * 1024 * 1024  # 10 MB，避免使用者上傳超大檔案塞爆磁碟/記憶體


# 教材 3.6：把使用者傳入的 filename 安全解析到 UPLOAD_DIR 之下，擋掉路徑穿越
def safe_upload_path(filename: str) -> str:
    base = os.path.realpath(settings.UPLOAD_DIR)
    target = os.path.realpath(os.path.join(base, filename))
    if target != base and not target.startswith(base + os.sep):
        raise HTTPException(400, "非法的檔名")
    return target


# ---------- 3.5 上傳 ----------


@router.post("/upload-only")
async def upload_image_only(file: UploadFile = File(...)):
    """單純上傳（不入庫，教材 3.5 範例）。

    示範完整的「驗證 → 讀取 → 產生唯一檔名 → 寫檔」流程。
    參數 file: UploadFile = File(...)：以 multipart/form-data 接收檔案，
    UploadFile 採串流，不會一次把整個檔案塞進記憶體。
    """
    # 1. 驗證 MIME 類型：擋掉非允許格式（例如使用者上傳 .exe 偽裝）
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"不支援的格式：{file.content_type}")

    # 2. 先用 file.size 擋掉過大的檔案，再讀進記憶體（避免大檔直接吃滿記憶體；
    #    真正的上限防線仍應在反向代理／伺服器層設定 body 大小）
    if file.size is not None and file.size > MAX_SIZE:
        raise HTTPException(413, "檔案過大（超過 10 MB）")
    content = await file.read()

    # 3. 產生唯一檔名：保留原副檔名，主檔名用 uuid 亂數避免衝突/覆蓋與路徑注入
    ext = os.path.splitext(file.filename or "")[1] or ".bin"  # 無副檔名時退回 .bin
    new_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, new_name)

    # 4. 確保上傳目錄存在（exist_ok=True 已存在不會出錯），以二進位模式寫入
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)

    # 回傳新檔名與原始資訊，方便前端後續以 new_name 取回檔案
    return {
        "filename": new_name,
        "original_name": file.filename,
        "size": len(content),
        "content_type": file.content_type,
    }


@router.post("/upload-multi")
async def upload_multi(files: List[UploadFile] = File(...)):
    """多張同時上傳（教材 3.5）。

    參數型別用 list[UploadFile]，前端在同一個欄位名（files）放多個檔案即可。
    此範例只回報每個檔案的名稱與大小，不實際寫檔。
    """
    results = []
    for file in files:  # 逐一處理每個上傳的檔案
        content = await file.read()  # 非同步讀取該檔內容
        results.append({"filename": file.filename, "size": len(content)})
    return {"count": len(results), "files": results}


@router.post("/upload-and-process")
async def upload_and_process(file: UploadFile = File(...)):
    """上傳並用 Pillow 處理（教材 3.5）。

    示範影像處理常見流程：讀取資訊 → 縮圖 → 轉檔壓縮 → 存檔。
    全程在記憶體（BytesIO）操作，最後才寫入磁碟。
    """
    content = await file.read()

    # 用 Pillow 開啟圖片；BytesIO 把 bytes 包成「類檔案物件」，省去先落地存檔
    # 非圖片或壞檔會丟 UnidentifiedImageError，包成 400 而非未處理的 500
    try:
        img = PILImage.open(BytesIO(content))
    except Exception:
        raise HTTPException(400, "無法解析的圖片檔")
    # 讀取原圖基本資訊（格式、色彩模式、寬高）
    info = {
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
    }

    # 縮圖：等比例縮到最長邊不超過 800px；thumbnail 會就地修改 img
    img.thumbnail((800, 800))
    # JPEG 不支援透明通道，RGBA / P（調色盤）需先轉成 RGB 才能存成 JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 存到記憶體緩衝區而非直接寫檔：quality 壓縮品質、optimize 進一步減少檔案大小
    output = BytesIO()
    img.save(output, format="JPEG", quality=85, optimize=True)

    # 縮圖檔名加 thumb_ 前綴並用 uuid 確保唯一，避免覆蓋原圖
    save_path = os.path.join(settings.UPLOAD_DIR, f"thumb_{uuid.uuid4().hex}.jpg")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(output.getvalue())  # getvalue() 取出緩衝區全部位元組

    return {
        "info": info,
        "thumbnail_size": len(output.getvalue()),
        "saved_to": save_path,
    }


# ---------- 3.6 圖片回傳 ----------


@router.get("/{filename}/download")
def download_image(filename: str):
    """FileResponse（教材 3.6）：最常用的回傳檔案方式。

    {filename} 是路徑參數，會被當成字串傳入。
    FileResponse 由 FastAPI 高效處理檔案讀取與串流，並設定正確的標頭。
    """
    file_path = safe_upload_path(filename)  # 先驗證、擋路徑穿越
    if not os.path.exists(file_path):
        raise HTTPException(404, "找不到檔案")
    # 省略 media_type 讓 FileResponse 依副檔名自動判斷；指定 filename 會帶上 Content-Disposition
    return FileResponse(file_path, filename=filename)


@router.get("/{filename}/stream")
def stream_image(filename: str):
    """串流回傳（教材 3.6）：適合大型檔案。

    用產生器（generator）每次只讀一小塊再吐出，記憶體用量固定，
    不會因檔案很大就一次全部載入。
    """
    file_path = safe_upload_path(filename)  # 先驗證、擋路徑穿越
    if not os.path.exists(file_path):
        raise HTTPException(404, "找不到檔案")

    # 產生器函式：每次讀 8KB，讀到空字串（檔案結束）時 while 結束、自動關檔
    def iterfile():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):  # := 海象運算子：邊賦值邊判斷
                yield chunk

    # 依副檔名判斷 MIME（StreamingResponse 不會自動判斷，需明確指定）
    media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    # StreamingResponse 接受一個可迭代物件，逐塊送給用戶端
    return StreamingResponse(iterfile(), media_type=media_type)


@router.get("/{filename}/base64")
def image_base64(filename: str):
    """Base64 回傳（教材 3.6，小圖適用）。

    把圖片編碼成 data URI 字串放進 JSON 回傳，前端可直接塞進 <img src>。
    缺點是體積會比原檔大約 1/3，故只建議用在小圖（如縮圖、icon）。
    """
    file_path = safe_upload_path(filename)  # 先驗證、擋路徑穿越
    if not os.path.exists(file_path):
        raise HTTPException(404, "找不到檔案")
    with open(file_path, "rb") as f:
        # b64encode 回傳的是 bytes，需再 decode 成 str 才能放進 JSON
        encoded = base64.b64encode(f.read()).decode()
    # 依副檔名判斷 MIME，組成 data URI 格式：data:<mime>;base64,<編碼內容>
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return {"filename": filename, "data": f"data:{mime};base64,{encoded}"}


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
        statement = statement.where(Image.title.icontains(keyword))  # icontains：不分大小寫
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


# ---------- 4.7 上傳並入庫 ----------


@router.post("/upload", response_model=ImagePublic, status_code=201)
async def upload_image(
    session: SessionDep,
    title: str = Form(...),
    file: UploadFile = File(...),
):
    """上傳檔案並寫入資料庫（檔案進磁碟，路徑進 DB）"""
    # 比照 /upload-only 驗證型別與大小（正式入庫端點也應把關）
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"不支援的格式：{file.content_type}")
    if file.size is not None and file.size > MAX_SIZE:
        raise HTTPException(413, "檔案過大（超過 10 MB）")
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
    2. 未命中 → 呼叫本機 AI 模型
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
