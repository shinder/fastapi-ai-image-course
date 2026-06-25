"""OpenAI gpt-image-1 影像生成（教材 6.6）

需安裝可選依賴：
    uv sync --extra openai
並在 .env 設定 OPENAI_API_KEY。

注意：舊的 dall-e-3 已於 2026 年退役，OpenAI 影像生成改用 gpt-image-1。最大差別是
gpt-image-1 **一律回傳 base64 影像資料**（不像 dall-e-3 給臨時 URL），所以這裡解碼後
落地存進 uploads/，再回傳可被前端存取的相對網址（搭配 main.py 掛載的 /uploads）。
"""

import base64
import os
import uuid

from app.config import settings


def generate_image(prompt: str) -> str:
    """產生圖片，存到 uploads/ 後回傳 /uploads/<檔名>。"""
    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        n=1,
        # 可選參數：quality="low"/"medium"/"high"、output_format="png"/"jpeg"
    )

    # gpt-image-1 一律回 base64（response.data[0].b64_json），沒有 url
    image_bytes = base64.b64decode(response.data[0].b64_json)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"gen_{uuid.uuid4().hex}.png"
    with open(os.path.join(settings.UPLOAD_DIR, filename), "wb") as f:
        f.write(image_bytes)
    return f"/uploads/{filename}"
