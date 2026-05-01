"""單元三 Pydantic / Form 示範路由（教材 3.2、3.3、3.4）

註：教材 2.4 的基本路由示範直接寫在 `app/main.py`，模擬還沒拆 APIRouter 之前的狀態。
"""
from datetime import datetime

from fastapi import APIRouter, Form

from app.schemas.image import ImageCreateRequest, ImageResponse

router = APIRouter(prefix="/api/v1", tags=["basic"])


# 教材 3.2 接收 JSON 請求
@router.post("/demo/images")
def demo_create_image(payload: ImageCreateRequest):
    return {
        "id": 1,
        "title": payload.title,
        "url": payload.url,
        "tags": payload.tags,
    }


# 教材 3.3 回應模型過濾內部欄位
@router.post("/demo/images-response", response_model=ImageResponse, status_code=201)
def demo_create_with_response_model(payload: ImageCreateRequest):
    record = {
        "id": 1,
        "title": payload.title,
        "url": payload.url,
        "uploaded_at": datetime.now(),
        "file_path": "/secret/internal/path",  # 不會出現在回應
    }
    return record


# 教材 3.4 表單資料
@router.post("/contact")
def submit_form(
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
):
    return {"name": name, "email": email, "message": message}
