"""FastAPI 入口（教材 2.3、2.4、2.5、2.6、3.6、4.3、5.3、5.7）"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.db.mongo import close_mongo, connect_mongo
from app.routes import ai, basic, images, mongo_demo, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    """啟動時建立資料表；如需預載 AI 模型可在此加 get_classifier() 等呼叫（教材 5.3）

    init_db() 與 connect_mongo() 連不到時都只印警告、不中斷啟動，
    讓沒用到該資料庫的路由仍可正常運作。
    """
    if init_db():
        print(f"✅ 資料庫連線成功：{settings.DATABASE_URL}")
    # 單元九：連線 MongoDB（連不到也不中斷啟動）
    await connect_mongo()
    # 例：from app.services.ai_service import get_classifier; get_classifier()
    yield
    # 關閉時清理資源
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態檔案掛載（教材 3.6）：把整個上傳目錄掛到 /uploads 路徑底下，
# 由 FastAPI（底層 Starlette）直接提供檔案，免自己為每個檔案寫路由。
# 掛載前先確保目錄存在，否則 StaticFiles 會在啟動時因找不到目錄而報錯。
# 之後 http://localhost:8000/uploads/<filename> 即可直接存取對應檔案。
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


# ---------- 教材 2.4 路由設計 ----------

# 基本路由 + 查詢參數
@app.get("/items")
def list_items(skip: int = 0, limit: int = 10, keyword: str | None = None):
    """查詢參數示範：GET /items?skip=0&limit=20&keyword=cat"""
    return {"skip": skip, "limit": limit, "keyword": keyword}


@app.post("/items")
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
