# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案性質

這是一個**教學範例專案**，搭配 FastAPI 與 AI 影像應用開發講義使用。每個檔案、甚至每個區塊都對應教材的某一節，docstring 與註解裡的「教材 X.Y」「單元 N」標記是刻意保留的，修改程式碼時請維持這些對照標記。教材原文可在 `docs/fastapi-ai-image.md`（symlink 至 Dropbox，已 gitignore）查閱。

因為是教學取向，程式碼以「清楚示範單一觀念」為優先，註解密度遠高於一般專案；新增或修改時請延續同樣的中文註解風格與詳細度。

## 常用指令

```bash
# 安裝核心依賴（不含重型 ML 套件）
uv sync

# 依教材章節加裝可選依賴
uv sync --extra ml       # 5.3 Hugging Face 分類（transformers + torch，很大）
uv sync --extra ocr      # 5.4 EasyOCR
uv sync --extra openai   # 5.5 / 5.6 OpenAI 相容介面、DALL·E
uv sync --extra vector   # 4.8 pgvector
uv sync --extra queue    # 6.11 RQ 任務佇列
uv sync --all-extras     # 全部

# 啟動依賴服務（PostgreSQL + Redis；MongoDB 需自行另開）
docker compose up -d

# 開發伺服器（http://localhost:8000，/docs 看 Swagger）
uv run fastapi dev app/main.py

# 測試
uv run pytest -q
uv run pytest tests/test_smoke.py::test_health   # 單一測試

# 格式化 / 靜態檢查（dev group 內，line-length 100）
uv run ruff format .
uv run ruff check .
uv run mypy app

# 任務佇列 worker（6.11，需先啟動 API 才有東西消費）
python -m app.workers.queue_worker                          # 方法一：手刻佇列
rq worker image-gen --url redis://localhost:6379/0          # 方法二：RQ（需 --extra queue）

# 客戶端 / requests 示範腳本
uv run python scripts/client.py
uv run python scripts/requests_demo.py
```

Python 版本鎖定 3.12（`requires-python = ">=3.12,<3.13"`）。

## 架構與關鍵慣例

### 應用組裝
`app/main.py` 是入口：定義 `lifespan`（啟動建表 + 連 Mongo、關閉清資源）、掛 CORS 與自製 `TimingMiddleware`、把 `uploads/` 目錄掛成 `/uploads` 靜態路由，最後 `include_router` 註冊各 APIRouter。教材 2.4 的基本路由刻意直接寫在 `main.py`（模擬還沒拆 router 的階段），其餘都拆進 `app/routes/`。

### 優雅降級（最重要的跨檔案設計）
所有外部依賴都做到「連不到也不讓 app 崩潰」，這是貫穿全專案的原則，修改時務必維持：
- **PostgreSQL**：`database.py` 的 `init_db()` 連不到只印警告、回 `False`。
- **MongoDB**：`db/mongo.py` 的 `connect_mongo()` 失敗時讓 `_client` 維持 `None`，`get_db()` 回 `None`，相關路由再回 503。
- **Redis**：`services/cache_service.py` 所有 helper（`cache_get/set/incr`…）捕捉 `redis.RedisError`，快取採「盡力而為」當未命中；`rate_limit.py` 與 `acquire_lock()` 採 **fail-open**（Redis 掛掉時放行 / 視為取得鎖）。

沒裝某個資料庫或服務時，用不到它的路由仍應正常運作——這是測試（`tests/test_smoke.py` 用不進 lifespan 的 `TestClient`）與設計的共同前提。

### 可選依賴用 lazy import
重型 / 可選套件（transformers、torch、easyocr、openai、rq）**一律在函式內 import**，不在模組頂層，這樣核心 `uv sync` 安裝下 app 仍能啟動，只有實際呼叫到該端點才會觸發 ImportError。`routes/ai.py` 的每個 AI 端點、`services/ai_service.py` 的 `get_classifier()` 都是這個模式。新增 AI 功能請照此辦理。

### 同步推論不阻塞事件循環
AI 推論是同步且耗時的，async 路由中一律用 `fastapi.concurrency.run_in_threadpool` 包起來呼叫（見 `routes/ai.py`）。模型本身用模組級單例快取（`ai_service._classifier`）避免每次請求重載。

### 依賴注入別名
用 `Annotated[..., Depends(...)]` 包成可重用型別別名：`SessionDep`（`database.py`，SQLModel Session）、`RedisDep`（`cache_service.py`，Redis client）。路由參數直接標這些別名即可。

### 兩套資料庫
- **PostgreSQL + SQLModel**（`models/image.py`）：影像 CRUD。採分層模型 `ImageBase / Image(table=True) / ImageCreate / ImagePublic / ImageUpdate`，分別對應基底、資料表、請求、回應、部分更新。`models/user.py` 是一對多 / 多對多關聯的純示範，預設未被 `init_db()` 載入。
- **MongoDB + PyMongo 原生 async**（`db/mongo.py`、`routes/mongo_demo.py`）：圖片留言。注意用的是 `AsyncMongoClient`（Motor 已棄用），非同步操作。

### 組態
`config.py` 用單純的 `Settings` 類別 + `os.getenv` 讀 `.env`（**非** pydantic-settings）。新增設定就在這裡加類別屬性。`.env.example` 是範本；本機開發預設 `DATABASE_URL=sqlite:///./app.db`，可改成 docker compose 起的 PostgreSQL。

### 上傳檔案安全
使用者可控檔名一律經 `safe_upload_path()`（`routes/images.py`）解析以擋路徑穿越；存檔用 `uuid` 重新命名。對外暴露的上傳端點（含 `routes/web.py` 的表單上傳）都做 MIME 白名單與大小上限驗證——因為 `uploads/` 會經 `/uploads` 直接對外提供，存入非圖片有資安風險。

### 背景任務 / 佇列的三種做法
`routes/ai.py` 的影像生成示範了三條路徑，狀態都存 Redis（`task:gen:{id}`，可跨 worker、可 TTL 自動清）：
1. `BackgroundTasks`（`/generate-async`）——同進程、回應後執行。
2. 手刻 Redis List `LPUSH`/`BRPOP`（`/generate-queued` + `workers/queue_worker.py`）。
3. RQ（`/generate-rq` + `services/tasks.py`，需 `--extra queue`）——注意 RQ 需要**未設 `decode_responses` 的獨立 Redis client**，不能共用快取那個連線池。
