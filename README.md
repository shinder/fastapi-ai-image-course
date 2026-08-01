# fastapi-ai-image

FastAPI 與 AI 影像應用開發的範例專案，內容對應講義 `fastapi-ai-image.md`（2026-08 改版）。

每一個檔案都對應教材中的某一節（原始碼註解裡的「教材 X.Y」即為節次），
方便學員閱讀程式碼時直接回去查文。

---

## 專案結構與教材對照

```txt
fastapi-ai-image/
├── pyproject.toml          # 教材 2.2 套件清單（核心 + 4 組可選）
├── docker-compose.yml      # 附錄 G PostgreSQL、附錄 E Redis
├── start.sh / start.bat            # 啟動開發伺服器（.sh 版會先起三個依賴容器）
├── start-postgres.sh / .bat        # 單獨啟動 PostgreSQL 容器（附錄 G）
├── start-redis.sh / .bat           # 單獨啟動 Redis 容器（附錄 E）
├── start-mongodb.sh / .bat         # 單獨啟動 MongoDB 容器（單元九）
├── stop-containers.sh / .bat       # 移除上述三個依賴容器（收工用，具名資料卷保留）
├── Dockerfile              # 教材 部署簡記
├── .env / .env.example     # 教材 2.2 環境變數
├── app/
│   ├── config.py           # 教材 2.2 Settings
│   ├── database.py         # 教材 5.4、5.6 engine、init_db、SessionDep
│   ├── main.py             # 教材 2.3、2.5、2.6、3.6、5.4 FastAPI 入口
│   ├── models/
│   │   ├── image.py        # 教材 5.5 SQLModel 影像表 + 多層模型
│   │   └── user.py         # 教材 5.5 一對多關聯範例
│   ├── schemas/
│   │   └── image.py        # 教材 3.1、3.2、3.3 純 Pydantic 範例
│   ├── routes/
│   │   ├── basic.py        # 教材 3.2、3.3、3.4 demo 路由（單元 2 路由直接寫在 main.py）
│   │   ├── images.py       # 教材 3.5、3.6、5.7、5.8、綜合實作
│   │   ├── images_raw.py   # 教材 5.x 對照：psycopg3 原生驅動，不經 ORM
│   │   ├── web.py          # 教材 6.2、6.7、6.11 Jinja2 頁面路由
│   │   ├── mongo_demo.py   # 教材 9.4 MongoDB 留言 CRUD
│   │   └── ai.py           # 教材 7.4、7.6、附錄 E、8.4、附錄 D
│   ├── services/
│   │   ├── ai_service.py            # 教材 附錄 D Hugging Face 分類
│   │   ├── ocr_service.py           # 教材 附錄 D EasyOCR
│   │   ├── ollama_service.py        # 教材 7.3、7.4 Ollama 視覺模型
│   │   ├── image_gen_service.py     # 教材 附錄 D OpenAI gpt-image-1
│   │   ├── external_ai.py           # 教材 8.4、附錄 C 外部 API
│   │   ├── memo_cache.py            # 教材 7.5 以圖片 hash 為 key 的記憶體快取
│   │   └── cache_service.py         # 教材 附錄 E Redis
│   ├── db/
│   │   └── mongo.py        # 教材 9.3 MongoDB 連線
│   ├── templates/          # 教材單元六 Jinja2 模板
│   │   ├── base.html       # 6.4 骨架（extends 的基底）
│   │   ├── index.html      # 6.9 圖片列表頁
│   │   └── upload.html     # 6.11 上傳表單頁（PRG）
│   ├── static/
│   │   ├── app.css         # 教材 6.7 專案自備樣式（驗證 /static 掛載）
│   │   └── demos/          # 教材單元四：瀏覽器端測試頁
│   │       ├── cors01.html         # 2.6 CORS 實測
│   │       ├── form01~04.html      # 4.2 HTML 表單四連發
│   │       ├── upload01~02.html    # 4.3 AJAX 上傳
│   │       ├── preview-01.html     # 4.4 createObjectURL 預覽
│   │       └── base64-01.html      # 4.4 FileReader / Base64
│   └── utils/
│       └── image_utils.py  # 教材 3.5 Pillow 工具
├── practices/              # 教材練習：可獨立執行的小範例（多數需先啟動 API）
│   ├── try_30~32_*.py      # generator / 模組匯入 / hashlib（5.1、3.7）
│   ├── try_40_mediapipe_hand.py  # 附錄 D MediaPipe 手部關鍵點
│   ├── try_01~03_*.py      # Pydantic（單元三）
│   ├── try_04~09_*.py      # tkinter 串接（單元三）
│   ├── try_10~18_*.py      # requests 串接 + 綜合應用（單元八）
│   └── try_20~27_*.py      # httpx 非同步串接（附錄 C）
├── requests/
│   └── api.http            # 教材 1.6 REST Client 測試檔（含綜合實作）
├── tests/
│   └── test_smoke.py       # 簡單冒煙測試
├── uploads/                # 上傳檔案儲存目錄
└── test_images/            # 測試用圖片放這裡（自備 cat.jpg、text.png）
```

---

## 快速開始

```bash
# 1. 安裝核心依賴
uv sync

# 2. 啟動開發伺服器（預設用 SQLite，不必先起任何容器）
uv run fastapi dev app/main.py
```

`.env` 預設 `DATABASE_URL=sqlite:///./app.db`，開箱即可跑。
要改用 PostgreSQL（教材 5.3）再啟動容器並改 `.env`：

```bash
docker compose up -d        # 或 ./start-postgres.sh
```

之後開瀏覽器：

- <http://localhost:8000>：根路由
- <http://localhost:8000/docs>：Swagger UI
- <http://localhost:8000/redoc>：ReDoc
- <http://localhost:8000/uploads/<filename>>：上傳檔案直存取

---

## 用腳本啟動 / 停止服務（替代 docker compose）

除了 `docker compose`，專案也附了一鍵腳本，改用單獨的 `docker run` 管理依賴服務容器
——比 docker compose 多含 MongoDB（單元九），`start.sh` 還會接著在前景啟動開發伺服器：

macOS / Linux：

```bash
./start.sh              # 啟動三個依賴容器（PostgreSQL / Redis / MongoDB），再前景跑開發伺服器（Ctrl-C 結束）
./stop-containers.sh    # 收工：移除這三個容器（具名資料卷保留，下次啟動自動接回資料）

# 也可單獨啟動某個服務
./start-postgres.sh
./start-redis.sh
./start-mongodb.sh
```

Windows（cmd / PowerShell）——內容與 `.sh` 版一致，只是換成批次檔語法：

```bat
start-postgres.bat
start-redis.bat
start-mongodb.bat
stop-containers.bat

start.bat               :: 啟動開發伺服器（含 --host 0.0.0.0，同網段裝置可連）
```

---

## 可選依賴（依教材章節）

核心 `uv sync` 不會安裝重型 ML 套件，請依需要選擇：

```bash
# 附錄 D Hugging Face 影像分類（會下載 transformers + torch，較大）
uv sync --extra ml

# 附錄 D EasyOCR
uv sync --extra ocr

# 附錄 D MediaPipe 手部／臉部／姿勢偵測（輕量本機模型）
uv sync --extra mediapipe
# 另需下載模型檔（7.8 MB，未進版控）：
mkdir -p ml_models
curl -o ml_models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

# 7.6 Ollama 的 OpenAI 相容介面 / 附錄 D gpt-image-1
uv sync --extra openai

# 附錄 G pgvector 向量搜尋
uv sync --extra vector

# 全部一次裝
uv sync --all-extras
```

---

## Ollama 設定（教材 7.3）

```bash
# 安裝 + 下載模型
brew install ollama          # 或從 https://ollama.com/download 下載
ollama pull gemma3:4b        # 或 qwen2.5vl:3b（繁中表現更好）

# 啟動服務（macOS / Windows 桌面版會自動啟動）
ollama serve
```

`.env` 中的 `OLLAMA_VISION_MODEL` 對應你下載的模型名稱。

---

## 測試

```bash
uv run pytest -q
```

冒煙測試只測不依賴外部服務的端點。需要 DB / Redis 的端點請用
`requests/api.http`（VSCode 的 REST Client 外掛）或 Swagger UI 操作。

---

## 程式碼格式化與檢查

本專案用 [Ruff](https://docs.astral.sh/ruff/)（已列在 dev 相依）統一排版與靜態檢查，
風格設定（line-length 100）寫在 `pyproject.toml` 的 `[tool.ruff]`：

```bash
uv run ruff format .   # 排版
uv run ruff check .    # Lint 檢查
```

VSCode 使用者：專案 `.vscode/settings.json` 已設定存檔時自動以 Ruff 排版，首次開啟
專案會提示安裝建議的擴充套件（見 `.vscode/extensions.json`）。其中
`ruff.importStrategy: "fromEnvironment"` 會直接使用專案 `.venv` 裡的 Ruff，不需另裝。

另外 `files.associations` 把 `app/templates/**/*.html` 關聯成 `jinja-html`
（需 Better Jinja 擴充套件）——模板檔名維持 `.html` 才能保有 Jinja 的 autoescape
（教材 6.3），但編輯時當成 Jinja 看，就不會被 HTML 檢查器一直報錯。
`app/static/demos/` 底下的純 HTML 測試頁不受影響。

---

## 主要 API

| Method | Path | 說明 | 教材 |
| ------ | ---- | ---- | ---- |
| GET    | `/health`                              | 健康檢查 | 2.3 |
| GET    | `/items`                               | 查詢參數示範 | 2.4 |
| POST   | `/items`                               | 基本 POST | 2.4 |
| GET    | `/items/{item_id}`                     | 路徑參數示範 | 2.4 |
| GET    | `/users/me` / `/users/{user_id}`       | 路徑順序示範 | 2.4 |
| POST   | `/api/v1/demo/images`                  | 接收 JSON | 3.2 |
| POST   | `/api/v1/demo/images-response`         | response_model | 3.3 |
| POST   | `/api/v1/contact`                      | Form 表單 | 3.4 |
| GET    | `/api/v1/images`                       | 列表（含 keyword） | 5.7 |
| POST   | `/api/v1/images`                       | JSON 建立 | 5.7 |
| GET    | `/api/v1/images/{id}`                  | 取得單筆 | 5.7 |
| PATCH  | `/api/v1/images/{id}`                  | 部分更新 | 5.7 |
| DELETE | `/api/v1/images/{id}`                  | 刪除 | 5.7 |
| GET    | `/api/v1/images/stats/total`           | 計數 | 5.7 |
| POST   | `/api/v1/images/upload-only`           | 純上傳（不入庫） | 3.5 |
| POST   | `/api/v1/images/upload-multi`          | 多張上傳 | 3.5 |
| POST   | `/api/v1/images/upload-and-process`    | 上傳 + Pillow 處理 | 3.5 |
| POST   | `/api/v1/images/upload`                | 上傳並入庫 | 5.8 |
| GET    | `/api/v1/images/{filename}/download`   | FileResponse | 3.6 |
| GET    | `/api/v1/images/{filename}/stream`     | StreamingResponse | 3.6 |
| GET    | `/api/v1/images/{filename}/base64`     | Base64 | 3.6 |
| POST   | `/api/v1/images/upload-and-describe`   | 綜合實作：上傳 + Ollama 描述 + 記憶體快取 + 入庫 | 綜合 |
| POST   | `/api/v1/images/upload-and-classify`   | 綜合（附錄版）：上傳 + Redis 快取 + HF 分類 + 入庫 | 綜合 |
| POST   | `/api/v1/ai/classify`                  | 影像分類（含快取） | 附錄 D、9.5 |
| POST   | `/api/v1/ai/ocr`                       | OCR 文字辨識 | 附錄 D |
| POST   | `/api/v1/ai/describe`                  | Ollama 圖片描述 | 7.4 |
| POST   | `/api/v1/ai/describe-cached`           | 同上，但先查記憶體快取 | 7.5 |
| GET    | `/api/v1/ai/describe-cached/stats`     | 記憶體快取命中率 | 7.5 |
| POST   | `/api/v1/ai/extract-invoice`           | 發票結構化抽取 | 7.4 |
| POST   | `/api/v1/ai/generate`                  | gpt-image-1 影像生成 | 附錄 D |
| POST   | `/api/v1/ai/generate-async`            | 背景任務生成 | 附錄 D |
| GET    | `/api/v1/ai/tasks/{task_id}`           | 查任務狀態 | 附錄 D |
| POST   | `/api/v1/ai/classify-external`         | 同步 requests 串接 | 8.4 |
| POST   | `/api/v1/ai/classify-external-async`   | 非同步 httpx 串接 | 附錄 C |
| GET    | `/api/v1/ai/cache/stats`               | 快取命中率 | 9.7 |
| GET    | `/api/v1/ai/cache-test`                | RedisDep 測試 | 9.4 |

---

## 練習範例（practices/）

```bash
# requests 串接小範例（單元八，try_10~17 各一個觀念，需先啟動 API）
uv run python practices/try_10_requests_get.py

# 綜合：模擬第三方串接（上傳辨識 + 查歷史）
uv run python practices/try_18_client_app.py
```

各範例的完整清單與說明見 [`practices/README.md`](practices/README.md)。
