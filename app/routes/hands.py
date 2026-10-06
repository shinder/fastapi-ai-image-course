"""MediaPipe 手部關鍵點偵測（教材 8.7）

兩條端點：
- POST /api/v1/hands/detect  只偵測，不存檔、不寫資料庫
- POST /api/v1/hands/upload  上傳存檔 + 偵測，結果寫進 images 表的 ai_result，
                             並另存一份同主檔名的 .json（附錄 D 的 H02 頁面打的是這條）

同一個前綴底下還有 WS /api/v1/hands/ws（即時串流，附錄 D 的 H03），放在 routes/hands_ws.py。

與 8.4 的 Ollama 端點是同一個模式：service 層負責推論、路由層只處理 HTTP，
阻塞的 CPU 工作一律用 run_in_threadpool 丟出去。
"""

import json
import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image as PILImage

from app.config import settings
from app.database import SessionDep
from app.models.image import Image
from app.services import hand_landmark

router = APIRouter(prefix="/api/v1/hands", tags=["hands"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 10 * 1024 * 1024


async def _read_upload(file: UploadFile) -> bytes:
    """共用的上傳檢查 + 讀檔，與 3.5 的上傳端點同一套規則"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"不支援的格式：{file.content_type}")

    if file.size is not None and file.size > MAX_SIZE:
        raise HTTPException(413, "檔案過大（超過 10 MB）")

    content = await file.read()

    # file.size 來自用戶端送的標頭，不一定有、也不一定可信，
    # 真的讀完之後再量一次才保險
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "檔案過大（超過 10 MB）")

    return content


def _check_model_ready() -> None:
    """模型沒載入就回 503（服務暫時不可用）。

    語意與 5.6 的 get_session() 一致：這是外部資源沒準備好，
    不是程式寫錯，不該回 500。
    """
    if not hand_landmark.is_ready():
        # 原因由 service 層記錄（套件沒裝 vs 模型檔沒下載），這裡只負責轉成 503
        raise HTTPException(503, hand_landmark.unavailable_reason())


async def _detect(content: bytes) -> dict:
    """呼叫偵測服務，把 Pillow 解析失敗轉成 400。

    detect() 是阻塞的 CPU 工作，一定要丟到 threadpool，
    否則會卡住事件迴圈，同時進來的其他請求全部要等。
    """
    try:
        return await run_in_threadpool(hand_landmark.detect, content)
    except (OSError, PILImage.DecompressionBombError) as exc:
        # PIL 解析不了的內容（例如副檔名是 .jpg 但其實不是圖）會丟 OSError；
        # 壓縮炸彈（很小的檔案解開後是超大圖）則是 DecompressionBombError
        raise HTTPException(400, f"無法解析圖檔：{exc}")


@router.post("/detect")
async def detect_hands(file: UploadFile = File(...)):
    """只做偵測：不存檔、不寫資料庫，回傳 21 個關鍵點的正規化座標。"""
    _check_model_ready()
    content = await _read_upload(file)
    result = await _detect(content)
    return {"original_name": file.filename, **result}


@router.post("/upload")
async def upload_and_detect(session: SessionDep, file: UploadFile = File(...)):
    """上傳存檔 + 偵測 + 把結果寫進 images 表的 ai_result 欄位，
    同時把偵測結果另存成一份 .json 檔，主檔名與圖檔相同。

    與 5.8 的儲存策略一致：檔案存檔案系統、中繼資料與 AI 結果進資料庫。
    """
    _check_model_ready()
    content = await _read_upload(file)

    # 先偵測再存檔：圖檔壞掉的話直接 400，不留下垃圾檔案
    result = await _detect(content)

    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    # 副檔名來自使用者給的檔名；剛好是 .json 的話，下面的 JSON 檔會把圖檔蓋掉
    if ext.lower() == ".json":
        ext = ".bin"

    # 主檔名（stem）先取出來，圖檔與 JSON 檔共用，
    # 這樣 uploads/ 裡的 abc123.jpg 與 abc123.json 一看就知道是同一組
    stem = uuid.uuid4().hex
    new_name = f"{stem}{ext}"
    json_name = f"{stem}.json"
    file_path = os.path.join(settings.UPLOAD_DIR, new_name)
    json_path = os.path.join(settings.UPLOAD_DIR, json_name)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # JSON 檔多存幾個檔案層面的欄位，單獨拿這個檔案出來看也知道對應哪張圖。
    # ensure_ascii=False 才不會把中文檔名寫成 \uXXXX 跳脫字串。
    # 這份 JSON 是伺服器自己產生的（不是使用者上傳的內容），放進 uploads/ 對外提供沒有疑慮
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(
            {
                "original_name": file.filename,
                "filename": new_name,
                "mime_type": file.content_type,
                "file_size": len(content),
                **result,
            },
            jf,
            ensure_ascii=False,
            indent=2,
        )

    image = Image(
        title=file.filename or new_name,
        filename=new_name,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        # ai_result 是 models/image.py 早就預留好的 JSON 欄位。
        # 結果裡已經帶了 model 與 mediapipe_version，
        # 之後接別的 AI 功能時才分得出這筆資料是誰產生的
        ai_result=result,
    )
    session.add(image)
    session.commit()
    session.refresh(image)

    return {
        "id": image.id,
        "original_name": file.filename,
        "filename": new_name,
        # uploads/ 有掛成靜態目錄（教材 3.6），這兩個網址可以直接在瀏覽器開起來看
        "url": f"/uploads/{new_name}",
        "json_filename": json_name,
        "json_url": f"/uploads/{json_name}",
        **result,
    }
