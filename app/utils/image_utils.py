"""影像處理小工具（教材 3.5 Pillow 範例）"""

import os
import uuid
from io import BytesIO

from PIL import Image

from app.config import settings


def make_thumbnail(content: bytes, max_size: tuple[int, int] = (800, 800)) -> bytes:
    """縮圖（不超過 max_size，保持比例）並轉 JPEG 壓縮"""
    img = Image.open(BytesIO(content))
    img.thumbnail(max_size)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    output = BytesIO()
    img.save(output, format="JPEG", quality=85, optimize=True)
    return output.getvalue()


def get_image_info(content: bytes) -> dict:
    """取得圖片基本資訊"""
    img = Image.open(BytesIO(content))
    return {
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
    }


def save_bytes(content: bytes, ext: str = ".jpg") -> str:
    """儲存 bytes 到 UPLOAD_DIR，回傳完整路徑"""
    new_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, new_name)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)
    return save_path
