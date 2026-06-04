"""單元三 Pydantic / Form 示範路由（教材 3.2、3.3、3.4）

本模組集中示範三件事：
1. 用 Pydantic 模型接收並驗證 JSON 請求主體（3.2）
2. 用 response_model 控制回應格式、過濾內部欄位（3.3）
3. 用 Form 接收 HTML 表單資料（3.4）

註：教材 2.4 的基本路由示範直接寫在 `app/main.py`，模擬還沒拆 APIRouter 之前的狀態。
"""
from datetime import datetime

from fastapi import APIRouter, Form

from app.schemas.image import ImageCreateRequest, ImageResponse

# APIRouter：把一組相關路由獨立成模組，最後在 main.py 用 include_router 掛上。
# prefix 會自動加在每條路徑前面，所以底下 "/demo/images" 實際路徑是 "/api/v1/demo/images"。
# tags 只影響自動產生的 API 文件（/docs）裡的分組顯示。
# 注意：路徑特意用 "/demo/..." 前綴，是為了避開 images.py 裡正式的 CRUD 路由
#       POST /api/v1/images，兩者若同路徑會在啟動時衝突。
router = APIRouter(prefix="/api/v1", tags=["basic"])


# 教材 3.2 接收 JSON 請求主體
@router.post("/demo/images")
def demo_create_image(payload: ImageCreateRequest):
    # 參數 payload 的型別標註為 ImageCreateRequest（Pydantic 模型），
    # FastAPI 會自動把 request body 的 JSON 解析並依模型規則驗證：
    # 例如 title 為空字串會直接回 422，不會進到這個函式。
    # 驗證通過後 payload 就是一個型別安全的物件，可用屬性存取（payload.title）。
    return {
        "id": 1,
        "title": payload.title,
        "url": payload.url,
        "tags": payload.tags,
    }


# 教材 3.3 回應模型過濾內部欄位
# response_model=ImageResponse：宣告「回應」要符合 ImageResponse 的結構，
#   FastAPI 會據此序列化並「過濾掉」模型沒列出的欄位（達到資安隔離）。
# status_code=201：建立成功的標準 HTTP 狀態碼（Created）。
@router.post("/demo/images-response", response_model=ImageResponse, status_code=201)
def demo_create_with_response_model(payload: ImageCreateRequest):
    # 這裡刻意回傳一個「比 ImageResponse 多了 file_path」的 dict，
    # 用來示範：即使函式回傳了內部欄位，response_model 也會把它濾掉。
    record = {
        "id": 1,
        "title": payload.title,
        "url": payload.url,
        "uploaded_at": datetime.now(),
        "file_path": "/secret/internal/path",  # 不在 ImageResponse 中 → 不會出現在回應
    }
    return record


# 教材 3.4 表單資料
# FastAPI 預設把參數當成 JSON / 查詢字串解析；要接收 HTML 表單
# （Content-Type: application/x-www-form-urlencoded 或 multipart）時，
# 必須用 Form(...) 明確標示，... 代表此欄位必填。
@router.post("/contact")
def submit_form(
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
):
    return {"name": name, "email": email, "message": message}
