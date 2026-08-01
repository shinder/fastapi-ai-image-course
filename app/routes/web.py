"""網頁與樣板路由（教材單元六）

用 Jinja2 做伺服器端渲染（SSR），提供這幾條路由：
- GET  /web         圖片列表頁：從 images 資料表查出資料再渲染（教材 6.10）
- GET  /web/users   用戶列表頁：表格渲染 + 分頁（教材 6.9）
- GET  /web/camera  相機拍照上傳頁：由現成 HTML 頁改寫成樣板（教材 6.12）
- GET  /web/upload  上傳表單頁：HTML 表單
- POST /web/upload  接收表單上傳、存檔並入庫，再重導回列表頁（PRG 模式，教材 6.11）

樣式主要用 Bootstrap CDN（見 templates/base.html）；另有少量專案自備樣式放在
app/static，由 main.py 掛載的 /static（StaticFiles，教材 6.7）提供。
圖片本身則由 main.py 掛載的 /uploads（StaticFiles）提供。

註：jinja2 已隨 fastapi[all] 一起安裝，不需另外加入相依。
"""

import os
import uuid

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.config import settings
from app.database import SessionDep
from app.models.image import Image
from app.models.user import User

# Jinja2Templates：指定樣板資料夾，之後用 templates.TemplateResponse 渲染 .html
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/web", tags=["web"])

# 圖片列表頁要顯示的副檔名
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
# 上傳允許的 MIME 類型（對應 IMAGE_EXTS）；後端驗證，不能只靠前端 accept
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.get("", response_class=HTMLResponse)
def gallery(request: Request, session: SessionDep, skip: int = 0, limit: int = 12):
    """圖片列表頁（教材 6.10）：從 images 資料表查出資料再渲染。

    早期版本是直接掃描 uploads/ 目錄，但那樣只拿得到檔名——標題、上傳時間、
    檔案大小這些中繼資料都在資料庫裡。改成查資料表後，頁面能顯示的資訊多得多，
    也和 5.7 的 JSON 端點用同一份資料來源。
    """
    stmt = select(Image).order_by(Image.id.desc()).offset(skip).limit(limit)
    images = session.exec(stmt).all()
    # Starlette 1.0 的新簽名：TemplateResponse(request, 樣板名, context)
    # request 必須傳入，樣板中才能使用 url_for 等功能
    return templates.TemplateResponse(
        request, "index.html", {"images": images, "skip": skip, "limit": limit}
    )


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, session: SessionDep, skip: int = 0, limit: int = 10):
    """用戶列表頁（教材 6.9）：把資料庫查出來的資料渲染成表格。

    與 GET /api/v1/users 是「同一份查詢、兩種輸出」：那條回 JSON，這條回 HTML。
    """
    stmt = select(User).offset(skip).limit(limit)
    users = session.exec(stmt).all()
    return templates.TemplateResponse(
        request, "users.html", {"users": users, "skip": skip, "limit": limit}
    )


@router.get("/camera", response_class=HTMLResponse)
def webrtc_page(request: Request):
    """相機拍照上傳頁（教材 6.12、4.6）：由一個現成的獨立 HTML 頁改寫而來。"""
    return templates.TemplateResponse(request, "webrtc.html")


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, error: str | None = None):
    """顯示上傳表單頁；error 不為 None 時於頁面顯示錯誤提示。"""
    return templates.TemplateResponse(request, "upload.html", {"error": error})


@router.post("/upload")
async def handle_upload(request: Request, session: SessionDep, file: UploadFile = File(...)):
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
    file_path = os.path.join(settings.UPLOAD_DIR, new_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # 檔案存檔案系統、中繼資料進資料庫（教材 5.8 的儲存策略），
    # 列表頁 gallery 才查得到這張圖
    image = Image(
        title=file.filename or new_name,
        filename=new_name,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    session.add(image)
    session.commit()

    # 重導到列表頁（gallery）；status_code=303 是 PRG 的標準作法
    return RedirectResponse(url=request.url_for("gallery"), status_code=303)
