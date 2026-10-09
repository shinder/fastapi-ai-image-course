# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案性質

這是一個**教學範例專案**，搭配 FastAPI 與 AI 影像應用開發講義使用。每個檔案、甚至每個區塊都對應教材的某一節，docstring 與註解裡的「教材 X.Y」「單元 N」標記是刻意保留的，修改程式碼時請維持這些對照標記。教材原文可在 `docs/fastapi-ai-image.md`（symlink 至 Dropbox，已 gitignore）查閱。

因為是教學取向，程式碼以「清楚示範單一觀念」為優先，註解密度遠高於一般專案；新增或修改時請延續同樣的中文註解風格與詳細度。

## 常用指令

```bash
# 全新 clone 先建立 .env（未進版控；缺少時 app 一 import 就失敗，見下方「組態」）
cp .env.example .env

# 安裝核心依賴（不含重型 ML 套件）
uv sync

# 依教材章節加裝可選依賴
uv sync --extra ml         # 附錄 D Hugging Face 分類（transformers + torch，很大）
uv sync --extra ocr        # 附錄 D EasyOCR
uv sync --extra openai     # 8.6 OpenAI 相容介面、附錄 D gpt-image-1
uv sync --extra mediapipe  # 8.7 MediaPipe 手部偵測
uv sync --extra vector     # 附錄 F pgvector
uv sync --all-extras     # 全部

# 8.7 手部模型檔（ml_models/hand_landmarker.task 已隨版控附上；下列腳本是遺失時的後援）
uv run python scripts/download_models.py --check   # 只驗證不下載
uv run python scripts/download_models.py           # 重新下載缺少的並比對 SHA-256

# 啟動依賴服務（PostgreSQL + Redis；MongoDB 需自行另開，見下方腳本）
docker compose up -d

# 或用腳本啟動（單獨 docker run，不需 docker compose，且比 compose 多含 MongoDB）
./sh-start-containers.sh # 起 PostgreSQL / Redis / MongoDB 三容器（不含開發伺服器）
./sh-start-postgres.sh   # 也可單獨啟動某個服務
./sh-start-redis.sh
./sh-start-mongodb.sh
./sh-stop-containers.sh  # 收工：移除上述三個容器（具名資料卷保留，下次啟動接回）
# 上述五支各有一份 cmd- 前綴的 .bat（Windows CMD 版，例：sh-start-containers.sh ↔ cmd-start-containers.bat）；
# sh-*.sh 在 Windows 需用 Git Bash 執行。兩套的相容性處理見下方「跨平台腳本」

# 開發伺服器（http://localhost:8080，/docs 看 Swagger）
uv run fastapi dev src/my_fastapi/main.py --port 8080
uv run my-fastapi          # 同上，走 pyproject [project.scripts] → src/my_fastapi/__init__.py 的 serve()
# 或用跨平台單行腳本：CMD 直接打 start.bat、bash 用 sh start.bat
# （內容是 uvicorn --host 0.0.0.0，順便供 4.5 的區網測試）

# 測試
uv run pytest -q
uv run pytest tests/test_smoke.py::test_health   # 單一測試

# 格式化 / 靜態檢查（dev group 內，line-length 100）
uv run ruff format .
uv run ruff check .
uv run mypy src

# 練習範例（practices/，可獨立執行；多數需先啟動 API）
uv run python practices/try_10_requests_get.py    # requests 小範例（單元七 try_10~17）
uv run python practices/try_18_client_app.py      # 綜合：模擬第三方串接
# try_30~32、try_40 的 docstring 指定用 -m 從專案根目錄執行；
# 其中 try_31 有 from practices.module_a import，直接跑檔案會 ModuleNotFoundError
uv run python -m practices.try_31_module
```

Python 版本鎖定 3.12（`requires-python = ">=3.12,<3.13"`）。

## 架構與關鍵慣例

### 套件佈局（uv init 的 src 佈局）
整個後端是 `src/my_fastapi/` 這一個套件（教材 2.2，uv 0.12 `uv init` 的預設佈局）。`pyproject.toml` 的 `[build-system]` 讓 `uv sync` 把它以可編輯模式裝進 `.venv`，所以 import 一律寫 `from my_fastapi.xxx import ...`，測試與 practices 也一樣，不靠「從根目錄執行」才找得到。建立方式是先開好資料夾、進入後 `uv init --name my-fastapi --python 3.12`；套件名 `my_fastapi` 由 `--name` 自動換算，不要在 pyproject 另設 `module-name`。開發伺服器統一用 8080 埠（`start.bat`、`uv run my-fastapi` 已指定；進入點函式叫 `serve()` 而不是 uv init 慣例的 `main()`，因為會被 `main.py` 子模組蓋掉；`fastapi dev` 預設是 8000，所以文件裡的指令都帶 `--port 8080`）。

路徑慣例：套件內的 `static/` 與 `templates/` 用 `Path(__file__)` 推算（`main.py` 的 `PACKAGE_DIR`、`routes/web.py`），不寫死相對於工作目錄的字串；`uploads/`、`ml_models/`、`.env`、`app.db` 則留在專案根目錄、由 `config.py` 用相對路徑指定，因此啟動伺服器與跑腳本仍要在專案根目錄。`Dockerfile` 因為專案本身會被建置安裝，`uv sync` 分成 `--no-install-project` 與複製 `src/` 之後的第二次，且 `.dockerignore` 不能排除 `README.md`（`readme` 欄位指到它）。

### 應用組裝
`src/my_fastapi/main.py` 是入口：定義 `lifespan`（啟動建表 + 連 Mongo、關閉清資源）、掛 CORS 與自製 `TimingMiddleware`、掛三個 `StaticFiles`（`uploads/` → `/uploads`，放使用者上傳的圖片，教材 3.6；`src/my_fastapi/static/` → `/static`，放專案自備的 CSS/JS，教材 6.7；`ml_models/` → `/models`，讓瀏覽器端推論的 H04 頁面下載模型檔，教材 附錄 D），最後 `include_router` 註冊各 APIRouter。教材 2.4 的基本路由刻意直接寫在 `main.py`（模擬還沒拆 router 的階段），其餘都拆進 `src/my_fastapi/routes/`。

樣式以 Bootstrap CDN 為主（見 `templates/base.html`），`src/my_fastapi/static/app.css` 只放少量自訂樣式，示範 `StaticFiles` 掛載搭配樣板裡 `url_for('static', path=...)` 反查網址的用法。

### 優雅降級（最重要的跨檔案設計）
所有外部依賴都做到「連不到也不讓 app 崩潰」，這是貫穿全專案的原則，修改時務必維持：
- **PostgreSQL**：`database.py` 的 `init_db()` 連不到只印警告、回 `False`；請求階段由 `get_session()` 把 `OperationalError` 轉成 503。Session 是惰性連線，錯誤要等路由執行查詢才拋出，所以 try/except 包的是 `yield`，不是 `with Session(...)` 那一行。
- **MongoDB**：`db/mongo.py` 的 `connect_mongo()` 失敗時讓 `_client` 維持 `None`，`get_db()` 回 `None`，相關路由再回 503。
- **Redis**：`services/cache_service.py` 所有 helper（`cache_get/set/incr`…）捕捉 `redis.RedisError`，快取採「盡力而為」當未命中；`rate_limit.py` 與 `acquire_lock()` 採 **fail-open**（Redis 掛掉時放行 / 視為取得鎖）。
- **MediaPipe**：`lifespan` 啟動段呼叫 `hand_landmark.load_detector()` 預載模型；套件沒裝或模型檔不存在時回 `False` 並記下原因，`routes/hands.py` 用 `is_ready()` / `unavailable_reason()` 回 503（訊息內含對應的安裝或下載指令）。WebSocket 版（`routes/hands_ws.py`）沒有狀態碼可用，改成先 `accept()`、送一則 `{"type": "error"}` 訊息，再以關閉碼 1011 斷線。

沒裝某個資料庫或服務時，用不到它的路由仍應正常運作——這是測試與設計的共同前提。`tests/test_smoke.py` 一律直接建構 `TestClient(app)`、不用 `with`，藉此跳過 lifespan（不建表、不連 Mongo、不載模型）；新增測試請沿用這個寫法，且不得依賴任何外部服務——Redis 用丟 `RedisError` 的 `MagicMock` 模擬，缺套件用 `monkeypatch.setitem(sys.modules, 名稱, None)` 模擬。

唯一沒有降級的是 `DATABASE_URL` 本身：見下方「組態」。

### 可選依賴用 lazy import
重型 / 可選套件（transformers、torch、easyocr、openai）**一律在函式內 import**，不在模組頂層，這樣核心 `uv sync` 安裝下 app 仍能啟動，只有實際呼叫到該端點才會觸發 ImportError。`routes/ai.py` 的每個 AI 端點、`services/ai_service.py` 的 `get_classifier()`、`services/hand_landmark.py`（mediapipe、numpy 放在 `load_detector()` / `decode_image()` / `detect()` 內）、`services/hand_stream.py`（放在 `HandStreamSession.__init__()` / `detect()` 內）都是這個模式。新增 AI 功能請照此辦理；`tests/test_smoke.py` 有測試守著 hand_landmark 與 hand_stream 不得在頂層 import 這兩個套件。

注意 `uv sync` 不帶 `--extra` 會把已裝的可選套件移除；本機開發環境慣用 `uv sync --all-extras`。

### 同步推論不阻塞事件迴圈
AI 推論是同步且耗時的，async 路由中一律用 `fastapi.concurrency.run_in_threadpool` 包起來呼叫（見 `routes/ai.py`）。模型本身用模組級單例快取（`ai_service._classifier`）避免每次請求重載。

### 依賴注入別名
用 `Annotated[..., Depends(...)]` 包成可重用型別別名：`SessionDep`（`database.py`，SQLModel Session）、`RedisDep`（`cache_service.py`，Redis client）。路由參數直接標這些別名即可。

### 兩套資料庫
- **PostgreSQL + SQLModel**（`models/image.py`）：影像 CRUD。採分層模型 `ImageBase / Image(table=True) / ImageCreate / ImagePublic / ImageUpdate`，分別對應基底、資料表、請求、回應、部分更新。`models/user.py` 是一對多 / 多對多關聯的示範，`routes/users.py` 有 import 它，所以四張表（users / user_images / tags / image_tag_links）啟動時會一起由 `init_db()` 建出。
- **MongoDB + PyMongo 原生 async**（`db/mongo.py`、`routes/mongo_demo.py`）：圖片留言。注意用的是 `AsyncMongoClient`（Motor 已棄用），非同步操作。

### 刻意並存的對照實作
下列幾組看起來像重複或沒接上線的程式碼，都是教材要拿來並排比較的，不要合併、刪除或「順手接上」：

- **`routes/images_raw.py` 沒有掛進 app**：它是 `images.py` 的 psycopg3 原生驅動對照版（路由前綴 `/api/v2/images`、資料表 `images_raw`），`main.py` 刻意不 `include_router`，啟用步驟寫在檔案開頭的 docstring。它自己讀環境變數 `PG_DSN`（libpq 格式，不能帶 `+psycopg`），不共用 `settings.DATABASE_URL`，因為後者預設是 SQLite。
- **`schemas/image.py` 與 `models/image.py`**：前者是單元三的純 Pydantic 範例（只有 `routes/basic.py` 的 demo 端點在用），後者是單元五的 SQLModel 分層模型。兩邊的類別名稱相近但互不相干。
- **`services/memo_cache.py` 與 `services/cache_service.py`**：前者是教材 8.5 的行程內 dict 快取（`/describe-cached` 使用），後者是附錄 E 的 Redis 版。前者的三個限制正是用來帶出後者，不要把前者改寫成 Redis。
- **requests 與 httpx**：`services/external_ai.py` 同步、非同步兩種寫法並存；`practices/try_20~27` 是 `try_10~17` 的 httpx 版，編號一一對應，改其中一支要看另一支是否需要同步調整。

### 組態
`config.py` 用單純的 `Settings` 類別 + `os.getenv` 讀 `.env`（**非** pydantic-settings）。新增設定就在這裡加類別屬性，並同步補進 `.env.example`。`.env.example` 是範本；本機開發預設 `DATABASE_URL=sqlite:///./app.db`，可改成 docker compose 起的 PostgreSQL。

`.env` 不進版控，而 `DATABASE_URL` 在 `config.py` 的後援值是空字串：缺 `.env` 時 `database.py` 模組頂層的 `create_engine("")` 會直接丟 `ArgumentError`，連 `import my_fastapi.main` 與 pytest 都跑不起來。遇到這個錯誤先確認 `.env` 是否存在。

### 上傳檔案安全
使用者可控檔名一律經 `safe_upload_path()`（`routes/images.py`）解析以擋路徑穿越；存檔用 `uuid` 重新命名。對外暴露的上傳端點（含 `routes/web.py` 的表單上傳）都做 MIME 白名單與大小上限驗證——因為 `uploads/` 會經 `/uploads` 直接對外提供，存入非圖片有資安風險。白名單與 10 MB 上限的常數在 `routes/images.py`、`routes/web.py`、`routes/hands.py` 各有一份（各檔自成一節教材，刻意不抽共用），調整規則時三處要一起改。`uploads/` 裡唯一的非圖片是 `/api/v1/hands/upload` 另存的 `.json`：那是伺服器自己產生的偵測結果，不是使用者上傳的內容。

### 手部關鍵點的三種做法（教材 附錄 D）
同一個模型放在三個位置跑的對照組，頁面在 `src/my_fastapi/static/demos/H02~H04-*.html`，各有一篇 `docs/H0x-*.md` 說明。改程式碼時對應的說明文件要一起改（文件裡有大量程式碼片段與回應範例）。

- **H02（單張上傳）**：`routes/hands.py` 的 `/upload`，用 `hand_landmark.py` 的全站單例 detector（IMAGE 模式）加一把鎖。除了寫進 `images.ai_result`，還會在 `uploads/` 另存一份同主檔名的 `.json`。
- **H03（WebSocket 串流）**：`routes/hands_ws.py` + `services/hand_stream.py`。**每條連線各建一個 VIDEO 模式的 detector，不可改成共用單例**：VIDEO 模式有跨影格狀態、時間戳必須嚴格遞增，共用會直接出錯。代價是每條連線吃一份模型記憶體，所以有 `HAND_WS_MAX_CONN`（預設 4）上限；`finally` 裡歸還名額與關閉 detector 的那段不能少。回壓由前端控制（同時只讓一格在路上）。
- **H04（瀏覽器端）**：沒有後端程式碼，頁面從 CDN 載入 `@mediapipe/tasks-vision`（版本寫死在網址，與 Python 端的 mediapipe 版本無關），模型檔從 `/models` 下載。

模型檔 `ml_models/hand_landmarker.task` 已進版控（H04 需要伺服器隨時供應得出來），也沒有被 `.dockerignore` 排除。

### 背景任務
`routes/ai.py` 的影像生成用 `BackgroundTasks`（`/generate-async`）示範：同進程、回應後才執行；任務狀態存 Redis（`task:gen:{id}`，可 TTL 自動清），再用 `/tasks/{task_id}` 查詢（教材 附錄 E）。

### 跨平台腳本（Windows）
五支腳本各有兩份實作，**用檔名前綴區分**：`sh-*.sh`（bash / Git Bash）與 `cmd-*.bat`（Windows
CMD），前綴之後的名稱一一對應（`sh-start-containers.sh` ↔ `cmd-start-containers.bat`）。**兩套是平行維護的，
改了其中一支，另一支要一起改**，行為與輸出訊息都應保持一致。新增腳本請延續這個命名慣例。
唯一的例外是 `start.bat`（啟動開發伺服器）：內容只有單行指令，兩種環境共用一份——
CMD 直接執行，bash 用 `sh start.bat`。

#### `sh-*.sh` 版：Git Bash 相容性
學生可能在 Windows 上用 Git Bash 跑 `sh-start*.sh` / `sh-stop-containers.sh`，新增或修改腳本時請維持兩項防護：

- **換行字元**：`.gitattributes` 已強制 `*.sh` 與 `Dockerfile` 以 `eol=lf` checkout。Git for Windows 預設 `core.autocrlf=true`，被轉成 CRLF 的腳本執行時只會報 `bad interpreter` 或 `$'\r': command not found`，看不出是換行問題。新增會交給 Linux 直譯器讀的檔案，記得一併納入。
- **MSYS 路徑轉換**：Git Bash 會把參數中看起來像 POSIX 絕對路徑的字串改寫成 Windows 路徑（`/data` → `C:/Program Files/Git/data`）。腳本只要帶了 `-v` / `--mount` 這類含絕對路徑的參數，開頭就要 `export MSYS_NO_PATHCONV=1` 與 `export MSYS2_ARG_CONV_EXCL='*'`（分別是 Git for Windows 專有與 MSYS2 原生，各版本認的不一定相同，兩個都設；macOS / Linux 直接忽略）。三支資料庫的 `sh-start-*.sh` 已設，`sh-stop-containers.sh` 與 `sh-start-containers.sh` 沒有路徑參數故不需要。

#### `cmd-*.bat` 版：CMD 的幾個坑
`.bat` 不是 `.sh` 的逐行直譯，改寫時有幾件事一定要顧到（現有五支都已處理，新增時比照）：

- **換行必須 CRLF**：`.gitattributes` 已加 `*.bat text eol=crlf`。只有 LF 時 cmd 對多行
  `for ( ... )` 區塊與 `goto` 標籤的解析會出錯，症狀跳痛（區塊只跑第一行、goto 說找不到標籤）。
- **中文編碼**：檔案存 **UTF-8 無 BOM**，並在 `@echo off` 後立刻 `chcp 65001 >nul`，否則中文在
  cp950 主控台是亂碼。**不可**存成 UTF-8 with BOM——cmd 不認 BOM，會把它併進第一行指令。
- **`echo` 裡的 `>` 要跳脫成 `^>`**：專案訊息慣用 `==>` / `-->` 開頭，沒跳脫會被當成輸出重導向，
  真的去建一個檔案。（`1>&2` 這種刻意導向 stderr 的則保持原樣。）
- **呼叫另一支 `.bat` 要加 `call`**：否則控制權一去不回，`cmd-start-containers.bat` 起完 postgres 就結束了。
- **沒有 `set -e`**：關鍵步驟後自己接 `if errorlevel 1`（語義是「>= 1」，即失敗）。
- **沒有 `sleep`**：用 `ping -n 2 127.0.0.1 >nul` 等約 1 秒。不用 `timeout /t 1`——標準輸入被
  重導向時它會直接報錯，被別的腳本呼叫時不可靠。
- **沒有 `echo -n`**：印進度點用 `<nul set /p "=."`。
- **不需要** MSYS 那兩個環境變數：路徑改寫是 Git Bash 特有行為，CMD 不會動 `-v` / `--mount` 的參數。

其餘 Windows 注意事項（Docker Desktop 維持 Linux 容器模式、`sh-*.sh` 版執行權限被拒改用
`bash sh-start-containers.sh`、`set DB_NAME=` 覆寫資料庫名）寫在 README 的「Windows 使用者」小節；
Windows 原生服務佔用埠號（5432 / 27017）的排除方式另見 `docs/stop-windows-services.md`。
