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
uv sync --extra ml       # 6.3 Hugging Face 分類（transformers + torch，很大）
uv sync --extra ocr      # 6.4 EasyOCR
uv sync --extra openai   # 6.5 / 6.6 OpenAI 相容介面、gpt-image-1
uv sync --extra vector   # 4.8 pgvector
uv sync --all-extras     # 全部

# 啟動依賴服務（PostgreSQL + Redis；MongoDB 需自行另開，見下方腳本）
docker compose up -d

# 或用腳本啟動（單獨 docker run，不需 docker compose，且比 compose 多含 MongoDB）
./sh-start.sh            # 起 PostgreSQL / Redis / MongoDB 三容器，再前景跑開發伺服器（Ctrl-C 結束）
./sh-start-postgres.sh   # 也可單獨啟動某個服務
./sh-start-redis.sh
./sh-start-mongodb.sh
./sh-stop-containers.sh  # 收工：移除上述三個容器（具名資料卷保留，下次啟動接回）
# 上述五支各有一份 cmd- 前綴的 .bat（Windows CMD 版，例：sh-start.sh ↔ cmd-start.bat）；
# sh-*.sh 在 Windows 需用 Git Bash 執行。兩套的相容性處理見下方「跨平台腳本」

# 開發伺服器（http://localhost:8000，/docs 看 Swagger）
uv run fastapi dev app/main.py

# 測試
uv run pytest -q
uv run pytest tests/test_smoke.py::test_health   # 單一測試

# 格式化 / 靜態檢查（dev group 內，line-length 100）
uv run ruff format .
uv run ruff check .
uv run mypy app

# 練習範例（practices/，可獨立執行；多數需先啟動 API）
uv run python practices/try_10_requests_get.py    # requests 小範例（單元七 try_10~17）
uv run python practices/try_18_client_app.py      # 綜合：模擬第三方串接
```

Python 版本鎖定 3.12（`requires-python = ">=3.12,<3.13"`）。

## 架構與關鍵慣例

### 應用組裝
`app/main.py` 是入口：定義 `lifespan`（啟動建表 + 連 Mongo、關閉清資源）、掛 CORS 與自製 `TimingMiddleware`、掛兩個 `StaticFiles`（`uploads/` → `/uploads`，放使用者上傳的圖片，教材 3.6；`app/static/` → `/static`，放專案自備的 CSS/JS，教材 6.7），最後 `include_router` 註冊各 APIRouter。教材 2.4 的基本路由刻意直接寫在 `main.py`（模擬還沒拆 router 的階段），其餘都拆進 `app/routes/`。

樣式以 Bootstrap CDN 為主（見 `templates/base.html`），`app/static/app.css` 只放少量自訂樣式，示範 `StaticFiles` 掛載搭配樣板裡 `url_for('static', path=...)` 反查網址的用法。

### 優雅降級（最重要的跨檔案設計）
所有外部依賴都做到「連不到也不讓 app 崩潰」，這是貫穿全專案的原則，修改時務必維持：
- **PostgreSQL**：`database.py` 的 `init_db()` 連不到只印警告、回 `False`。
- **MongoDB**：`db/mongo.py` 的 `connect_mongo()` 失敗時讓 `_client` 維持 `None`，`get_db()` 回 `None`，相關路由再回 503。
- **Redis**：`services/cache_service.py` 所有 helper（`cache_get/set/incr`…）捕捉 `redis.RedisError`，快取採「盡力而為」當未命中；`rate_limit.py` 與 `acquire_lock()` 採 **fail-open**（Redis 掛掉時放行 / 視為取得鎖）。

沒裝某個資料庫或服務時，用不到它的路由仍應正常運作——這是測試（`tests/test_smoke.py` 用不進 lifespan 的 `TestClient`）與設計的共同前提。

### 可選依賴用 lazy import
重型 / 可選套件（transformers、torch、easyocr、openai）**一律在函式內 import**，不在模組頂層，這樣核心 `uv sync` 安裝下 app 仍能啟動，只有實際呼叫到該端點才會觸發 ImportError。`routes/ai.py` 的每個 AI 端點、`services/ai_service.py` 的 `get_classifier()` 都是這個模式。新增 AI 功能請照此辦理。

### 同步推論不阻塞事件迴圈
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

### 背景任務
`routes/ai.py` 的影像生成用 `BackgroundTasks`（`/generate-async`）示範：同進程、回應後才執行；任務狀態存 Redis（`task:gen:{id}`，可 TTL 自動清），再用 `/tasks/{task_id}` 查詢（教材 附錄 E）。

### 跨平台腳本（Windows）
五支腳本各有兩份實作，**用檔名前綴區分**：`sh-*.sh`（bash / Git Bash）與 `cmd-*.bat`（Windows
CMD），前綴之後的名稱一一對應（`sh-start.sh` ↔ `cmd-start.bat`）。**兩套是平行維護的，
改了其中一支，另一支要一起改**，行為與輸出訊息都應保持一致。新增腳本請延續這個命名慣例。

#### `sh-*.sh` 版：Git Bash 相容性
學生可能在 Windows 上用 Git Bash 跑 `sh-start*.sh` / `sh-stop-containers.sh`，新增或修改腳本時請維持兩項防護：

- **換行字元**：`.gitattributes` 已強制 `*.sh` 與 `Dockerfile` 以 `eol=lf` checkout。Git for Windows 預設 `core.autocrlf=true`，被轉成 CRLF 的腳本執行時只會報 `bad interpreter` 或 `$'\r': command not found`，看不出是換行問題。新增會交給 Linux 直譯器讀的檔案，記得一併納入。
- **MSYS 路徑轉換**：Git Bash 會把參數中看起來像 POSIX 絕對路徑的字串改寫成 Windows 路徑（`/data` → `C:/Program Files/Git/data`）。腳本只要帶了 `-v` / `--mount` 這類含絕對路徑的參數，開頭就要 `export MSYS_NO_PATHCONV=1` 與 `export MSYS2_ARG_CONV_EXCL='*'`（分別是 Git for Windows 專有與 MSYS2 原生，各版本認的不一定相同，兩個都設；macOS / Linux 直接忽略）。三支 `sh-start-*.sh` 已設，`sh-stop-containers.sh` 與 `sh-start.sh` 沒有路徑參數故不需要。

#### `cmd-*.bat` 版：CMD 的幾個坑
`.bat` 不是 `.sh` 的逐行直譯，改寫時有幾件事一定要顧到（現有五支都已處理，新增時比照）：

- **換行必須 CRLF**：`.gitattributes` 已加 `*.bat text eol=crlf`。只有 LF 時 cmd 對多行
  `for ( ... )` 區塊與 `goto` 標籤的解析會出錯，症狀跳痛（區塊只跑第一行、goto 說找不到標籤）。
- **中文編碼**：檔案存 **UTF-8 無 BOM**，並在 `@echo off` 後立刻 `chcp 65001 >nul`，否則中文在
  cp950 主控台是亂碼。**不可**存成 UTF-8 with BOM——cmd 不認 BOM，會把它併進第一行指令。
- **`echo` 裡的 `>` 要跳脫成 `^>`**：專案訊息慣用 `==>` / `-->` 開頭，沒跳脫會被當成輸出重導向，
  真的去建一個檔案。（`1>&2` 這種刻意導向 stderr 的則保持原樣。）
- **呼叫另一支 `.bat` 要加 `call`**：否則控制權一去不回，`cmd-start.bat` 起完 postgres 就結束了。
- **沒有 `set -e`**：關鍵步驟後自己接 `if errorlevel 1`（語義是「>= 1」，即失敗）。
- **沒有 `sleep`**：用 `ping -n 2 127.0.0.1 >nul` 等約 1 秒。不用 `timeout /t 1`——標準輸入被
  重導向時它會直接報錯，被別的腳本呼叫時不可靠。
- **沒有 `echo -n`**：印進度點用 `<nul set /p "=."`。
- **不需要** MSYS 那兩個環境變數：路徑改寫是 Git Bash 特有行為，CMD 不會動 `-v` / `--mount` 的參數。

其餘 Windows 注意事項（Docker Desktop 維持 Linux 容器模式、`sh-*.sh` 版執行權限被拒改用
`bash sh-start.sh`、`set DB_NAME=` 覆寫資料庫名）寫在 README 的「Windows 使用者」小節；
Windows 原生服務佔用埠號（5432 / 27017）的排除方式另見 `docs/stop-windows-services.md`。
