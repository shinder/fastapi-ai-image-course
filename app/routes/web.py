"""網頁與樣板路由（教材單元八，補充教材）

用 Jinja2 做伺服器端渲染（SSR），提供三條路由：
- GET  /web         圖片列表頁：掃描 uploads/ 目錄列出已上傳的圖片
- GET  /web/upload  上傳表單頁：HTML 表單
- POST /web/upload  接收表單上傳、存檔，再重導回列表頁（PRG 模式）

樣式主要用 Bootstrap CDN（見 templates/base.html）；另有少量專案自備樣式放在
app/static，由 main.py 掛載的 /static（StaticFiles，教材 8.5）提供。
圖片本身則由 main.py 掛載的 /uploads（StaticFiles）提供。

註：jinja2 已隨 fastapi[all] 一起安裝，不需另外加入相依。
"""

import os
import uuid

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings

# Jinja2Templates：指定樣板資料夾，之後用 templates.TemplateResponse 渲染 .html
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/web", tags=["web"])

# 圖片列表頁要顯示的副檔名
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
# 上傳允許的 MIME 類型（對應 IMAGE_EXTS）；後端驗證，不能只靠前端 accept
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.get("", response_class=HTMLResponse)
def gallery(request: Request):
    """圖片列表頁：掃描 uploads/ 目錄，把圖片檔名交給樣板渲染。"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filenames = [
        name
        for name in sorted(os.listdir(settings.UPLOAD_DIR))
        if os.path.splitext(name)[1].lower() in IMAGE_EXTS
    ]
    # Starlette 1.0 的新簽名：TemplateResponse(request, 樣板名, context)
    # request 必須傳入，樣板中才能使用 url_for 等功能
    return templates.TemplateResponse(request, "index.html", {"images": filenames})


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, error: str | None = None):
    """顯示上傳表單頁；error 不為 None 時於頁面顯示錯誤提示。"""
    return templates.TemplateResponse(request, "upload.html", {"error": error})


@router.post("/upload")
async def handle_upload(request: Request, file: UploadFile = File(...)):
    """接收表單上傳：存檔後重導回列表頁。

    這裡用 PRG（Post/Redirect/Get）模式：處理完 POST 後回 303 重導到 GET 頁面，
    使用者重新整理時就不會重複送出表單。
    """
    # 後端驗證型別：upload.html 的 accept="image/*" 只是前端提示，可被繞過；
    # 且 uploads/ 會透過 /uploads 對外提供，存入非圖片（如 .html/.svg）有資安風險
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        # PRG：重導回上傳頁並以 query 帶出錯誤，仍走無副作用的 GET
        url = request.url_for("upload_page").include_query_params(error="type")
        return RedirectResponse(url=url, status_code=303)

    content = await file.read()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    new_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(settings.UPLOAD_DIR, new_name), "wb") as f:
        f.write(content)

    # 重導到列表頁（gallery）；status_code=303 是 PRG 的標準作法
    return RedirectResponse(url=request.url_for("gallery"), status_code=303)
