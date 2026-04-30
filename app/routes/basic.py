"""基本路由示範（教材 2.4、2.5、3.2、3.3、3.4）"""
from datetime import datetime

from fastapi import APIRouter, Form
from pydantic import BaseModel, Field

from app.schemas.image import ImageCreateRequest, ImageResponse

router = APIRouter(prefix="/api/v1", tags=["basic"])


# 教材 2.4 基本路由
@router.get("/items")
def list_items(skip: int = 0, limit: int = 10, keyword: str | None = None):
    """查詢參數示範：GET /api/v1/items?skip=0&limit=20&keyword=cat"""
    return {"skip": skip, "limit": limit, "keyword": keyword}


@router.post("/items")
def create_item():
    return {"id": 3, "created": True}


# 路徑參數（教材 2.4）
@router.get("/items/{item_id}")
def get_item(item_id: int):
    """型別提示自動驗證；傳入 /items/abc 會回 422"""
    return {"id": item_id}


# 路徑順序的重要性（教材 2.4）：具體路徑放在參數路徑之前
@router.get("/users/me")
def get_current_user():
    return {"id": "current"}


@router.get("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}


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
