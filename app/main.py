"""FastAPI 入口（教材 2.3、2.4、2.5、2.6、3.6、4.3、5.3、5.7）"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db
from app.db.mongo import close_mongo, connect_mongo
from app.routes import ai, basic, images, mongo_demo, web

# 主控台日誌（教材 2.6）：root 維持 WARNING，只讓自家 app.access 輸出 INFO，
# 避免把 httpx 等第三方套件的 INFO 訊息也一起印出來
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("app.access")
logger.setLevel(logging.INFO)


class TimingMiddleware(BaseHTTPMiddleware):
    """計時中介軟體（教材 2.6）：量測請求處理時間，寫入回應標頭並記錄 log"""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"
        logger.info(
            "%s %s -> %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期（教材 4.3、5.3）：定義 app「啟動時」與「關閉時」各跑一次的程式碼。

    lifespan 是一個 async context manager，用 yield 把它切成兩半：
    - yield 之前：啟動階段（開始收請求之前執行）→ 建表、連 Mongo，也可在此預載 AI 模型。
    - yield 之後：關閉階段（停止服務之後執行）→ 釋放資源。
    注意：整個 app 只各跑一次（非每個請求都跑）；多 worker 部署時，每個行程會各跑一遍。
    它取代了已棄用的 @app.on_event("startup"/"shutdown")，是目前官方推薦寫法。

    init_db() 與 connect_mongo() 連不到時都只印警告、不中斷啟動，
    讓沒用到該資料庫的路由仍可正常運作（優雅降級）。
    """
    # ---- yield 之前：啟動階段 ----
    if init_db():
        print(f"資料庫連線成功：{settings.DATABASE_URL}")
    # 單元九：連線 MongoDB（連不到也不中斷啟動）
    await connect_mongo()
    # 想避免「第一個請求才載入模型」的冷啟動延遲，可在這裡預載（教材 5.3）：
    #   from app.services.ai_service import get_classifier; get_classifier()
    yield  # ← app 在此進入服務狀態，處理所有請求
    # ---- yield 之後：關閉階段（清理資源）----
    await close_mongo()


app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI AI 服務",
    version="0.0.1",
    lifespan=lifespan,
)

# CORS 設定（教材 2.6，開發階段允許所有來源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # 搭配 allow_origins=["*"] 時須為 False
    allow_methods=["*"],
    allow_headers=["*"],
)

# 計時中介軟體（教材 2.6）；後加 → 較外層，計時涵蓋 CORS 與路由
app.add_middleware(TimingMiddleware)

# 靜態檔案掛載（教材 3.6）：把整個上傳目錄掛到 /uploads 路徑底下，
# 由 FastAPI（底層 Starlette）直接提供檔案，免自己為每個檔案寫路由。
# 掛載前先確保目錄存在，否則 StaticFiles 會在啟動時因找不到目錄而出錯。
# 之後 http://localhost:8000/uploads/<filename> 即可直接存取對應檔案。
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 靜態檔案掛載（教材 8.5）：另外把 app/static 掛到 /static，提供「專案自備」的 CSS/JS。
# 與上面 /uploads 的差別：/uploads 放「使用者上傳」的檔案，/static 放「開發者預先準備」的
# 靜態資源（樣式、前端腳本、圖示等）。
# base.html 會用 url_for('static', path='app.css') 反查這裡的網址來載入樣式，
# 路徑日後改了樣板也不必跟著改。
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


# ---------- 教材 2.4 路由設計 ----------


@app.get("/items")
def list_items():
    return [{"id": 1}, {"id": 2}]


# 基本路由 + 查詢參數
@app.get("/my-items")
def my_list_items(skip: int = 0, limit: int = 10, keyword: str | None = None):
    """查詢參數示範：GET /items?skip=0&limit=20&keyword=cat"""
    return {"skip": skip, "limit": limit, "keyword": keyword}


@app.post("/items", status_code=201)
def create_item():
    return {"id": 3, "created": True}


# 路徑參數：型別提示自動驗證，傳入 /items/abc 會回 422
@app.get("/items/{item_id}")
def get_item(item_id: int):
    return {"id": item_id}


# 路徑順序的重要性：具體路徑（/users/me）必須放在參數路徑（/users/{user_id}）之前
@app.get("/users/me")
def get_current_user():
    return {"id": "current"}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}


# ---------- 教材 2.5 註冊各 APIRouter ----------

app.include_router(basic.router)
app.include_router(images.router)
app.include_router(ai.router)
app.include_router(web.router)  # 單元八（補充教材）：Jinja2 樣板網頁
app.include_router(mongo_demo.router)  # 單元九（補充教材）：MongoDB 留言
