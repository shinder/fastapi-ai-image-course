# fastapi-ai-image

FastAPI 與 AI 影像應用開發的範例專案，內容對應講義
[`fastapi-ai-image-2604.md`](https://example.com/handout)。

每一個檔案都對應教材中的某一節，方便學員閱讀程式碼時直接回去查文。

---

## 專案結構與教材對照

```txt
fastapi-ai-image/
├── pyproject.toml          # 教材 2.2 套件清單（核心 + 4 組可選）
├── docker-compose.yml      # 教材 4.2、6.2 PostgreSQL + Redis
├── Dockerfile              # 教材 部署簡記
├── .env / .env.example     # 教材 2.2 環境變數
├── app/
│   ├── config.py           # 教材 2.2 Settings
│   ├── database.py         # 教材 4.3、4.5 engine、init_db、SessionDep
│   ├── main.py             # 教材 2.3、2.5、2.6、3.6、4.3 FastAPI 入口
│   ├── models/
│   │   ├── image.py        # 教材 4.4 SQLModel 影像表 + 多層模型
│   │   └── user.py         # 教材 4.4 一對多關聯範例
│   ├── schemas/
│   │   └── image.py        # 教材 3.1、3.2、3.3 純 Pydantic 範例
│   ├── routes/
│   │   ├── basic.py        # 教材 2.4、3.2、3.3、3.4 基本路由
│   │   ├── images.py       # 教材 3.5、3.6、4.6、4.7、綜合實作
│   │   └── ai.py           # 教材 5.3、5.4、5.5、5.6、5.7、6.5、7.5
│   ├── services/
│   │   ├── ai_service.py            # 教材 5.3 Hugging Face 分類
│   │   ├── ocr_service.py           # 教材 5.4 EasyOCR
│   │   ├── ollama_service.py        # 教材 5.5 Ollama 視覺模型
│   │   ├── image_gen_service.py     # 教材 5.6 OpenAI DALL·E
│   │   ├── external_ai.py           # 教材 7.5、7.6 外部 API
│   │   └── cache_service.py         # 教材 6.4、6.5、6.6 Redis
│   └── utils/
│       └── image_utils.py  # 教材 3.5 Pillow 工具
├── scripts/
│   ├── client.py           # 教材 綜合實作 客戶端腳本
│   └── requests_demo.py    # 教材 7.2、7.3、7.4 requests 用法
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

# 2. 啟動 PostgreSQL + Redis
docker compose up -d

# 3. 啟動 FastAPI 開發伺服器
uv run fastapi dev app/main.py
```

之後開瀏覽器：

- <http://localhost:8000>：根路由
- <http://localhost:8000/docs>：Swagger UI
- <http://localhost:8000/redoc>：ReDoc
- <http://localhost:8000/uploads/<filename>>：上傳檔案直存取

---

## 可選依賴（依教材章節）

核心 `uv sync` 不會安裝重型 ML 套件，請依需要選擇：

```bash
# 單元 5.3 Hugging Face 影像分類（會下載 transformers + torch，較大）
uv sync --extra ml

# 單元 5.4 EasyOCR
uv sync --extra ocr

# 單元 5.5 進階（Ollama OpenAI 相容介面）/ 單元 5.6 DALL·E
uv sync --extra openai

# 單元 4.8 pgvector 向量搜尋
uv sync --extra vector

# 全部一次裝
uv sync --all-extras
```

---

## Ollama 設定（單元 5.5）

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

## 主要 API

| Method | Path | 說明 | 教材 |
| ------ | ---- | ---- | ---- |
| GET    | `/health`                              | 健康檢查 | 2.3 |
| GET    | `/api/v1/items`                        | 查詢參數示範 | 2.4 |
| GET    | `/api/v1/items/{item_id}`              | 路徑參數示範 | 2.4 |
| GET    | `/api/v1/users/me` / `/{user_id}`      | 路徑順序示範 | 2.4 |
| POST   | `/api/v1/demo/images`                  | 接收 JSON | 3.2 |
| POST   | `/api/v1/demo/images-response`         | response_model | 3.3 |
| POST   | `/api/v1/contact`                      | Form 表單 | 3.4 |
| GET    | `/api/v1/images`                       | 列表（含 keyword） | 4.6 |
| POST   | `/api/v1/images`                       | JSON 建立 | 4.6 |
| GET    | `/api/v1/images/{id}`                  | 取得單筆 | 4.6 |
| PATCH  | `/api/v1/images/{id}`                  | 部分更新 | 4.6 |
| DELETE | `/api/v1/images/{id}`                  | 刪除 | 4.6 |
| GET    | `/api/v1/images/stats/total`           | 計數 | 4.6 |
| POST   | `/api/v1/images/upload-only`           | 純上傳（不入庫） | 3.5 |
| POST   | `/api/v1/images/upload-multi`          | 多張上傳 | 3.5 |
| POST   | `/api/v1/images/upload-and-process`    | 上傳 + Pillow 處理 | 3.5 |
| POST   | `/api/v1/images/upload`                | 上傳並入庫 | 4.7 |
| GET    | `/api/v1/images/{filename}/download`   | FileResponse | 3.6 |
| GET    | `/api/v1/images/{filename}/stream`     | StreamingResponse | 3.6 |
| GET    | `/api/v1/images/{filename}/base64`     | Base64 | 3.6 |
| POST   | `/api/v1/images/upload-and-classify`   | 綜合：上傳 + 快取 + 分類 + 入庫 | 綜合 |
| POST   | `/api/v1/ai/classify`                  | 影像分類（含快取） | 5.3、6.5 |
| POST   | `/api/v1/ai/ocr`                       | OCR 文字辨識 | 5.4 |
| POST   | `/api/v1/ai/describe`                  | Ollama 圖片描述 | 5.5 |
| POST   | `/api/v1/ai/extract-invoice`           | 發票結構化抽取 | 5.5 |
| POST   | `/api/v1/ai/generate`                  | DALL·E 影像生成 | 5.6 |
| POST   | `/api/v1/ai/generate-async`            | 背景任務生成 | 5.6 |
| GET    | `/api/v1/ai/tasks/{task_id}`           | 查任務狀態 | 5.6 |
| POST   | `/api/v1/ai/classify-external`         | 同步 requests 串接 | 7.5 |
| POST   | `/api/v1/ai/classify-external-async`   | 非同步 httpx 串接 | 7.6 |
| GET    | `/api/v1/ai/cache/stats`               | 快取命中率 | 6.7 |
| GET    | `/api/v1/ai/cache-test`                | RedisDep 測試 | 6.4 |

---

## 客戶端腳本

```bash
# 模擬第三方串接（綜合實作）
uv run python scripts/client.py

# Requests 套件用法示範
uv run python scripts/requests_demo.py
```
