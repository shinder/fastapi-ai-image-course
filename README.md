# fastapi-ai-image-course

FastAPI 與 AI 影像應用開發的範例專案，內容對應講義 `fastapi-ai-image.md`（版本日期見講義首頁）。

每一個檔案都對應教材中的某一節（原始碼註解裡的「教材 X.Y」即為節次），
方便學員閱讀程式碼時直接回去查文。

---

## 專案結構與教材對照

```txt
fastapi-ai-image-course/
├── pyproject.toml          # 教材 2.2 套件清單（核心 + 5 組可選）
├── docker-compose.yml      # 附錄 F PostgreSQL、附錄 E Redis
├── start.bat               # 啟動開發伺服器的單行腳本（CMD 直接執行；bash 用 sh start.bat）
├── sh-start-containers.sh  # 一鍵起三個依賴容器（替代 docker compose；不含伺服器）
├── sh-start-postgres.sh    # 單獨啟動 PostgreSQL 容器（附錄 F）
├── sh-start-redis.sh       # 單獨啟動 Redis 容器（附錄 E）
├── sh-start-mongodb.sh     # 單獨啟動 MongoDB 容器（單元九）
├── sh-stop-containers.sh   # 移除上述三個依賴容器（收工用，具名資料卷保留）
├── cmd-*.bat               # 上述五支 sh-*.sh 的 Windows CMD 版（cmd-start-containers.bat…）
├── Dockerfile              # 教材 部署簡記
├── .env / .env.example     # 教材 2.2 環境變數
├── src/my_fastapi/         # 教材 2.2 uv init 的 src 佈局：整個後端都在這個套件裡
│   ├── __init__.py         # 教材 2.2 uv init 產生；serve() 給 uv run my-fastapi 啟動伺服器
│   ├── config.py           # 教材 2.2 Settings
│   ├── database.py         # 教材 5.4、5.6 engine、init_db、SessionDep
│   ├── main.py             # 教材 2.3、2.4、2.5、2.6、3.6、5.4、6.7、8.7、附錄 B、附錄 D FastAPI 入口
│   ├── models/
│   │   ├── image.py        # 教材 5.5 SQLModel 影像表 + 多層模型
│   │   └── user.py         # 教材 5.5 一對多／多對多關聯範例
│   ├── schemas/
│   │   └── image.py        # 教材 3.1、3.2、3.3 純 Pydantic 範例
│   ├── routes/
│   │   ├── basic.py        # 教材 3.2、3.3、3.4 demo 路由（單元 2 路由直接寫在 main.py）
│   │   ├── images.py       # 教材 3.5、3.6、5.7、5.8
│   │   ├── images_raw.py   # 教材 5.x 對照：psycopg3 原生驅動，不經 ORM
│   │   ├── users.py        # 教材 5.7 User CRUD（關聯示範表實際會建出）
│   │   ├── web.py          # 教材 6.9~6.12 Jinja2 頁面路由
│   │   ├── mongo_demo.py   # 教材 9.4 MongoDB 留言 CRUD
│   │   ├── hands.py        # 教材 8.7 MediaPipe 手部偵測（單張上傳；附錄 D 的 H02 也用它）
│   │   ├── hands_ws.py     # 教材 附錄 D WebSocket 手部串流（H03）
│   │   └── ai.py           # 教材 8.4、8.6、附錄 E、7.4、附錄 D
│   ├── services/
│   │   ├── ai_service.py            # 教材 附錄 D Hugging Face 分類
│   │   ├── ocr_service.py           # 教材 附錄 D EasyOCR
│   │   ├── ollama_service.py        # 教材 8.3、8.4 Ollama 視覺模型
│   │   ├── image_gen_service.py     # 教材 附錄 D OpenAI gpt-image-1
│   │   ├── external_ai.py           # 教材 7.4、附錄 C 公開 API（Picsum / Dog CEO）
│   │   ├── hand_landmark.py         # 教材 8.7 MediaPipe 手部偵測（Tasks API）
│   │   ├── hand_stream.py           # 教材 附錄 D 串流用偵測器（每條連線一個，VIDEO 模式）
│   │   ├── memo_cache.py            # 教材 8.5 以圖片 hash 為 key 的記憶體快取
│   │   └── cache_service.py         # 教材 附錄 E Redis
│   ├── db/
│   │   └── mongo.py        # 教材 9.3 MongoDB 連線
│   ├── templates/          # 教材單元六 Jinja2 模板
│   │   ├── base.html       # 6.4 骨架（extends 的基底）
│   │   ├── navbar.html     # 6.5、6.8 導覽列片段（include）
│   │   ├── index.html      # 6.10 圖片列表頁
│   │   ├── users.html      # 6.9 用戶列表頁
│   │   ├── camera.html     # 6.12 相機拍照上傳頁
│   │   └── upload.html     # 6.11 上傳表單頁（PRG）
│   ├── static/
│   │   ├── app.css         # 教材 6.7 專案自備樣式（驗證 /static 掛載）
│   │   └── demos/          # 教材單元四：瀏覽器端測試頁
│   │       ├── cors01.html         # 2.6 CORS 實測
│   │       ├── form01~04.html      # 4.2 HTML 表單四連發
│   │       ├── upload01~02.html    # 4.3 AJAX 上傳
│   │       ├── preview-01.html     # 4.4 createObjectURL 預覽
│   │       ├── base64-01.html      # 4.4 FileReader / Base64
│   │       ├── H02-hands-1.html    # 附錄 D 手部關鍵點：單張上傳，後端推論
│   │       ├── H03-hands-ws.html   # 附錄 D 手部關鍵點：WebSocket 串流，後端推論
│   │       └── H04-hands-live.html # 附錄 D 手部關鍵點：瀏覽器端 WASM 推論
│   └── utils/
│       └── image_utils.py  # 教材 3.5 Pillow 工具
├── docs/                   # 補充文件
│   ├── H02-hands-upload.md       # 附錄 D 手部關鍵點三種做法的實作說明（H02 單張上傳）
│   ├── H03-hands-ws.md           # 同上（H03 WebSocket 串流）
│   ├── H04-hands-live.md         # 同上（H04 瀏覽器端推論）
│   └── stop-windows-services.md  # Windows 原生服務佔用埠號時的停用／恢復指南
├── ml_models/              # 教材 8.7 MediaPipe 模型檔（hand_landmarker.task，已隨版控附上）
├── scripts/
│   └── download_models.py  # 教材 8.7 模型檔遺失時重新下載＋SHA-256 驗證
├── practices/              # 教材練習：可獨立執行的小範例（多數需先啟動 API）
│   ├── try_30~32_*.py      # generator / 模組匯入 / hashlib（5.1、3.7）
│   ├── try_40_mediapipe_hand.py  # 教材 8.7 MediaPipe 手部關鍵點
│   ├── try_01~03_*.py      # Pydantic（單元三）
│   ├── try_04~09_*.py      # tkinter 串接（參考範例；打單元三的端點）
│   ├── try_10~18_*.py      # requests 串接 + 綜合應用（單元七）
│   └── try_20~27_*.py      # httpx 非同步串接（附錄 C）
├── requests/
│   └── api.http            # 教材 1.6 REST Client 測試檔
├── tests/
│   └── test_smoke.py       # 簡單冒煙測試
├── uploads/                # 上傳檔案儲存目錄
└── test_images/            # 測試用圖片放這裡（自備 cat.jpg、text.png）
```

---

## 專案是怎麼建出來的（教材 2.2）

採用 uv 0.12 `uv init` 預設的 **src 佈局**：整個後端是 `src/my_fastapi/` 這一個套件，
`pyproject.toml` 有 `[build-system]`（uv_build）與 `[project.scripts]`，講義第 2 章從這個指令開始：

```bash
# 1. 先建好專案資料夾並進入，再在裡面 uv init；--name 指定專案名（資料夾名可以不同）
#    產生：pyproject.toml、.python-version、README.md、src/my_fastapi/__init__.py
mkdir fastapi-ai-image-course
cd fastapi-ai-image-course
uv init --name my-fastapi --python 3.14

# 2. 加入核心套件（其餘套件在教到的那一節再 uv add，見講義 2.2 的安裝時機表）
uv add "fastapi[all]"
uv add --dev pytest ruff mypy

# 3. 之後的程式碼都放進 src/my_fastapi/，main.py 是 FastAPI 入口
```

套件名 `my_fastapi` 是 uv 由 `--name my-fastapi` 自動換算的（連字號改底線），不必另外設定；資料夾名與專案名無關。

---

## 快速開始

```bash
# 1. 安裝核心依賴
uv sync

# 2. 啟動開發伺服器（預設用 SQLite，不必先起任何容器）；兩種寫法擇一
uv run fastapi dev src/my_fastapi/main.py --port 8080   # fastapi CLI，自動重載
uv run my-fastapi                           # pyproject.toml [project.scripts]，呼叫 my_fastapi.serve()
```

`uv sync` 除了裝第三方套件，也會把 `src/my_fastapi` 以可編輯模式裝進 `.venv`（`pyproject.toml`
的 `[build-system]`），所以程式裡一律寫 `from my_fastapi.xxx import ...`，從哪個目錄執行都找得到。
不過 `uploads/`、`ml_models/` 與 `.env` 都放在專案根目錄、用相對路徑指定，啟動伺服器仍請在專案根目錄執行。

`.env` 預設 `DATABASE_URL=sqlite:///./app.db`，開箱即可跑。
要改用 PostgreSQL（教材 5.3）再啟動容器並改 `.env`：

```bash
docker compose up -d        # 或 ./sh-start-postgres.sh
```

之後開瀏覽器：

- <http://localhost:8080>：根路由
- <http://localhost:8080/docs>：Swagger UI
- <http://localhost:8080/redoc>：ReDoc
- <http://localhost:8080/uploads/<filename>>：上傳檔案直存取

---

## 用腳本啟動 / 停止服務（替代 docker compose）

除了 `docker compose`，專案也附了一鍵腳本，改用單獨的 `docker run` 管理依賴服務容器
——比 docker compose 多含 MongoDB（單元九）。開發伺服器則用單行腳本 `start.bat` 啟動（見下）。

同一件事各有兩份實作，**用檔名前綴區分，選一套用就好**；
唯一例外是 `start.bat`——內容只有單行指令，兩種環境共用一份：

| 前綴 | 版本 | 執行環境 |
| --- | --- | --- |
| `sh-*.sh` | bash 版 | macOS / Linux 的終端機、Windows 的 Git Bash |
| `cmd-*.bat` | Windows CMD 版 | Windows 的 CMD 或 PowerShell |

macOS / Linux：

```bash
./sh-start-containers.sh   # 啟動三個依賴容器（PostgreSQL / Redis / MongoDB）
sh start.bat               # 前景啟動開發伺服器（--host 0.0.0.0；Ctrl-C 結束）
./sh-stop-containers.sh    # 收工：移除這三個容器（具名資料卷保留，下次啟動自動接回資料）

# 也可單獨啟動某個服務
./sh-start-postgres.sh
./sh-start-redis.sh
./sh-start-mongodb.sh
```

### Windows 使用者

#### 先決條件

- **Docker Desktop**：維持預設的 **Linux 容器模式**（腳本用到的 tmpfs 掛載需要它）。
- **uv**：已安裝且在 PATH 中——`start.bat` 用 `uv run` 啟動伺服器。
- **Git for Windows**：只有要跑 `sh-*.sh` 版才需要（Git Bash 是它內附的）；走 `cmd-*.bat` 版可以不裝。

#### 建議走 CMD 版（`cmd-*.bat`）

在 CMD 或 PowerShell 直接執行，不需要 Git Bash：

```bat
cmd-start-containers.bat
start.bat
cmd-stop-containers.bat

rem 也可單獨啟動某個服務
cmd-start-postgres.bat
cmd-start-redis.bat
cmd-start-mongodb.bat
```

- PowerShell 執行要加 `.\`（例：`.\cmd-start-containers.bat`）；`.bat` 是交給 cmd.exe 跑的，
  不受 PowerShell 執行原則（ExecutionPolicy）限制。
- 想換資料庫名稱：CMD 是先 `set DB_NAME=my_db`、PowerShell 是先 `$env:DB_NAME="my_db"`，
  再執行 `cmd-start-postgres.bat`，並同步改 `.env` 的 `DATABASE_URL`。
- 這些 `.bat` 開頭都有 `chcp 65001`，把主控台切成 UTF-8，中文訊息才不會變亂碼
  （繁中 Windows 的 cmd 預設是 cp950）；副作用是這個視窗之後的編碼也會維持 UTF-8。

#### 改用 bash 版（`sh-*.sh`）

請在 **Git Bash** 執行（不是 CMD 或 PowerShell），指令與上面 macOS / Linux 那段完全相同：

- `./sh-start-containers.sh` 若因執行權限被拒，改用 `bash sh-start-containers.sh`。
- `sh start.bat` 前景跑的 uvicorn，在 Git Bash 下 Ctrl-C 偶爾要按兩次才停得下來。
- 腳本開頭已關掉 MSYS 的路徑自動轉換，`-v` / `--mount` 的掛載路徑不會被改寫成 Windows 路徑，
  這點不必自己處理。

#### 常見問題

**容器起不來，說 5432 / 27017 / 6379 被佔用**

多半是你先前用安裝程式裝過 PostgreSQL 或 MongoDB，那些服務開機就自動啟動了。
判斷是誰佔著埠號、以及停用／恢復的完整步驟見
[`docs/stop-windows-services.md`](docs/stop-windows-services.md)。

**在 CMD 輸入 `sh-start-containers.sh` 跳出「選擇開啟方式」對話框**

`.sh` 不是 CMD 能執行的東西。改用 `cmd-start-containers.bat`，或到 Git Bash 裡執行。

**Git Bash 執行 `.sh` 報 `bad interpreter` 或 `$'\r': command not found`**

工作目錄裡的腳本被轉成 CRLF 了（Git for Windows 預設 `core.autocrlf=true`）。
`.gitattributes` 已強制 `*.sh` 以 LF checkout，若你是在加入這項設定「之前」clone 的，
重新 clone 一份即可。

**訊息裡的中文是亂碼**

`cmd-*.bat` 版已自行 `chcp 65001` 不會有這問題；若是你自己開的視窗（例如要看 `docker logs`），
先執行一次 `chcp 65001` 再操作。

---

## 可選依賴（依教材章節）

核心 `uv sync` 不會安裝重型 ML 套件，請依需要選擇：

```bash
# 附錄 D Hugging Face 影像分類（會下載 transformers + torch，較大）
uv sync --extra ml

# 附錄 D EasyOCR
uv sync --extra ocr

# 8.7、附錄 D MediaPipe 手部／臉部／姿勢偵測（輕量本機模型）
# 注意：不支援 Intel Mac（MediaPipe 的 macOS x86_64 wheel 停在 0.10.21）。
# 另外這個 extra 會連帶裝進 opencv-contrib-python（wheel 約 56 MB，整組下載約 110 MB），下載需要一點時間。
uv sync --extra mediapipe
# 模型檔（ml_models/hand_landmarker.task，約 7.5 MB）已隨版控附上，clone 下來就能用。
# 開課前／上課前可以驗一次，確認檔案完整（比對 SHA-256，不重新下載）：
uv run python scripts/download_models.py --check
# 萬一檔案遺失或損毀，重新下載：
uv run python scripts/download_models.py

# 8.6 Ollama 的 OpenAI 相容介面 / 附錄 D gpt-image-1
uv sync --extra openai

# 附錄 F pgvector 向量搜尋
uv sync --extra vector

# 全部一次裝
uv sync --all-extras
```

> **`uv sync` 會把沒指定的 extra 移除**：裝過 `--extra mediapipe` 之後，若再跑一次不帶參數的
> `uv sync`（例如 pull 完順手同步），mediapipe 會被靜默拆掉，端點只剩 503。要保留就每次帶一樣的
> `--extra`，或改用 `uv sync --inexact`（不移除多出來的套件）。

---

## 手部關鍵點的三種做法（教材 附錄 D）

同一個模型（`ml_models/hand_landmarker.task`）放在三個不同的位置跑，拿來對照延遲、頻寬與伺服器負載。
啟動伺服器後直接開下列頁面：

| 頁面 | 推論在哪 | 傳輸方式 | 用途 | 說明文件 |
| --- | --- | --- | --- | --- |
| `/static/demos/H02-hands-1.html` | 後端 Python | `POST` 單張圖 | 上傳存檔 + 寫進資料庫，圖與 JSON 同主檔名存在 `uploads/` | [docs/H02](docs/H02-hands-upload.md) |
| `/static/demos/H03-hands-ws.html` | 後端 Python | WebSocket 串流 | 即時追蹤，示範 backpressure（回壓） | [docs/H03](docs/H03-hands-ws.md) |
| `/static/demos/H04-hands-live.html` | 瀏覽器 WASM | 不傳，影像不離開本機 | 即時追蹤，零頻寬零伺服器負載 | [docs/H04](docs/H04-hands-live.md) |

`docs/` 裡三篇分別把前後端的溝通方式與運作流程拆開講，包含資料格式、設計取捨與常見問題。

- **H02、H03 需要後端的 MediaPipe**：先 `uv sync --extra mediapipe`。沒裝時 app 照常啟動，
  H02 的端點回 503、H03 的 WebSocket 會收到一則說明原因的錯誤訊息後被關閉。
- **H04 不需要**：推論在瀏覽器裡跑，伺服器只負責供應 HTML 與模型檔（`/models/hand_landmarker.task`）。
- **攝影機只在 `localhost` 或 HTTPS 下可用**：用區網 IP 開這些頁面時瀏覽器會拒絕開啟攝影機，
  要用教材 4.5 的 cloudflared 開 HTTPS 通道。

在 M3 Mac 上的實測數字（640x480、`mediapipe` 0.10.35）：

| 項目 | 數字 |
| --- | --- |
| Python IMAGE 模式（H02） | 27.3 ms |
| Python VIDEO 模式（H03） | 16.9 ms，追蹤省掉手掌偵測，快四成 |
| 瀏覽器 WASM + WebGL（H04） | 16.0~16.8 ms，跟原生 Python 一樣快 |
| H03 端到端來回 | 約 18~19 ms，其中網路與 JPEG 編碼約 3 ms |
| 640x480 → 320x240 | 17.3 ms，**沒有變快**，模型內部本來就會縮到 192/224 |

兩個容易搞錯的直覺：**降解析度只省頻寬、不會加速推論**；**後端跑不會比瀏覽器快**。
所以純粹要即時追蹤的話，H04 客觀上是最好的選擇；H03 這種後端串流合理的時機，
是伺服器要做用戶端做不到的事（例如比對資料庫、跨使用者彙整）。

---

## Ollama 設定（教材 8.3）

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

`tests/test_smoke.py` 是冒煙測試，只測不依賴外部服務的端點；`tests/test_layout.py`
守住 src 佈局的約定（套件從 `src/` 安裝、static 與樣板不依賴工作目錄、`serve()` 進入點與埠號一致）。
需要 DB / Redis 的端點請用
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

另外 `files.associations` 把 `src/my_fastapi/templates/**/*.html` 關聯成 `jinja-html`
（需 Better Jinja 擴充套件）——模板檔名維持 `.html` 才能保有 Jinja 的 autoescape
（教材 6.3），但編輯時當成 Jinja 看，就不會被 HTML 檢查器一直報錯。
`src/my_fastapi/static/demos/` 底下的純 HTML 測試頁不受影響。

---

## 主要 API

| Method | Path | 說明 | 教材 |
| ------ | ---- | ---- | ---- |
| GET    | `/health`                              | 健康檢查 | 2.3 |
| GET    | `/items`                               | 基本路由 | 2.4 |
| GET    | `/my-items`                            | 查詢參數示範 | 2.4 |
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
| POST   | `/api/v1/ai/classify`                  | 影像分類（含 Redis 快取） | 附錄 D、附錄 E |
| POST   | `/api/v1/ai/ocr`                       | OCR 文字辨識 | 附錄 D |
| POST   | `/api/v1/ai/describe`                  | Ollama 圖片描述 | 8.4 |
| POST   | `/api/v1/ai/describe-cached`           | 同上，但先查記憶體快取 | 8.5 |
| POST   | `/api/v1/hands/detect`                 | MediaPipe 手部關鍵點（只偵測） | 8.7 |
| POST   | `/api/v1/hands/upload`                 | 手部偵測 + 存檔入庫，另存同主檔名的 `.json` | 8.7、附錄 D |
| WS     | `/api/v1/hands/ws`                     | 手部即時串流（送 JPEG 影格、回座標 JSON） | 附錄 D |
| GET    | `/api/v1/ai/describe-cached/stats`     | 記憶體快取命中率 | 8.5 |
| POST   | `/api/v1/ai/extract-invoice`           | 發票結構化抽取 | 8.4 |
| POST   | `/api/v1/ai/generate`                  | gpt-image-1 影像生成 | 附錄 D |
| POST   | `/api/v1/ai/generate-async`            | 背景任務生成 | 附錄 D、附錄 E |
| GET    | `/api/v1/ai/tasks/{task_id}`           | 查任務狀態 | 附錄 E |
| POST   | `/api/v1/ai/import-random`             | 從公開圖庫抓圖存檔入庫 | 7.4 |
| GET    | `/api/v1/ai/fetch-many`                | 並行抓多張圖 | 附錄 C |
| GET    | `/api/v1/ai/cache/stats`               | Redis 快取命中率 | 附錄 E |
| GET    | `/api/v1/ai/cache-test`                | RedisDep 測試 | 附錄 E |
| GET    | `/api/v1/users`                        | 用戶列表 | 5.7 |
| GET    | `/api/v1/users/{user_id}`              | 取得單一用戶（含關聯圖片） | 5.7 |
| POST   | `/api/v1/users`                        | 建立用戶 | 5.7 |
| DELETE | `/api/v1/users/{user_id}`              | 刪除用戶 | 5.7 |
| GET    | `/web` / `/web/users` / `/web/camera`  | Jinja2 頁面（列表／用戶／相機） | 6.9~6.12 |
| GET    | `/web/upload`                          | 上傳表單頁 | 6.11 |
| POST   | `/web/upload`                          | 表單上傳（PRG） | 6.11 |

---

## 練習範例（practices/）

```bash
# requests 串接小範例（單元七，try_10~17 各一個觀念，需先啟動 API）
uv run python practices/try_10_requests_get.py

# 綜合：模擬第三方串接（上傳入庫 + 查歷史）
uv run python practices/try_18_client_app.py
```

各範例的完整清單與說明見 [`practices/README.md`](practices/README.md)。
