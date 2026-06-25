# practices/ 教材練習範例

搭配《FastAPI 與 AI 影像應用》講義的可獨立執行小範例。命名慣例 `try_NN_主題.py`，
每個檔聚焦單一觀念、編號大致依教材單元順序；各檔開頭的 docstring 都有詳細說明與對應的後端端點。

## 一、Pydantic 資料驗證（純本地，教材 3.1）

不需啟動後端，直接執行即可觀察 Pydantic 的驗證與轉換行為。

| 檔案 | 主題 |
| --- | --- |
| `try_01_pydantic.py` | 定義基本資料模型（BaseModel、型別標註） |
| `try_02_pydantic.py` | 用 Field 設定欄位限制與預設值 |
| `try_03_pydantic.py` | 用 field_validator 自訂驗證邏輯 |

## 二、tkinter 桌面 GUI 串接（需後端，教材 3.2～3.5）

用 tkinter 做一個小視窗，示範桌面程式怎麼把資料送給 FastAPI。
`try_04`～`06` 是基礎版，`try_07`～`09` 是對應的 **Thread 進階版**（把請求丟到背景執行緒，避免送出時視窗凍結）。

| 檔案 | 主題 | 對應後端端點 | 教材 |
| --- | --- | --- | --- |
| `try_04_tkinter_json.py` | 送 JSON | `POST /api/v1/demo/images` | 3.2 |
| `try_05_tkinter_form.py` | 送表單 | `POST /api/v1/contact` | 3.4 |
| `try_06_tkinter_upload.py` | 上傳圖片 | `POST /api/v1/images/upload-only` | 3.5 |
| `try_07_tkinter_json_thread.py` | 送 JSON（Thread 版） | 同 `try_04` | 3.2 |
| `try_08_tkinter_form_thread.py` | 送表單（Thread 版） | 同 `try_05` | 3.4 |
| `try_09_tkinter_upload_thread.py` | 上傳圖片（Thread 版） | 同 `try_06` | 3.5 |

## 三、requests HTTP 串接（需後端，教材 5.2～5.4 + 綜合）

用 requests 套件打本專案在前面單元寫好的 API，每個觀念拆成一個小範例。

| 檔案 | 主題 | 對應後端端點 | 教材 |
| --- | --- | --- | --- |
| `try_10_requests_get.py` | 基本 GET | `GET /api/v1/images/{id}` | 5.2 |
| `try_11_requests_post.py` | 基本 POST（送 JSON） | `POST /api/v1/images` | 5.2 |
| `try_12_requests_exceptions.py` | 例外處理 | `GET /api/v1/images/{id}` | 5.2 |
| `try_13_requests_query.py` | Query / Headers / Cookies | `GET /api/v1/images` | 5.3 |
| `try_14_requests_upload.py` | 上傳檔案（multipart） | `POST /api/v1/images/upload` | 5.3 |
| `try_15_requests_session.py` | Session 連線重用 | `GET /users/me`、`/api/v1/images` | 5.3 |
| `try_16_requests_retry.py` | 自動重試機制 | `GET /api/v1/images` | 5.3 |
| `try_17_requests_auth.py` | 三種認證機制的帶法 | （示意 URL，不實連） | 5.4 |
| `try_18_client_app.py` | 綜合：模擬第三方串接 | `upload-and-classify`、`/api/v1/images` | 綜合 |

## 執行方式

純本地範例（`try_01`～`try_03`，以及只示範寫法的 `try_17`）直接執行：

```bash
uv run python practices/try_01_pydantic.py
```

需要後端的範例，先啟動開發伺服器（另開一個終端機），再執行範例：

```bash
# 終端機 1：啟動後端（需 docker compose 的 PostgreSQL，見專案根目錄 README）
uvicorn app.main:app --reload

# 終端機 2：執行範例
uv run python practices/try_11_requests_post.py
```

補充說明：

- tkinter 範例（`try_04`～`try_09`）會開啟 GUI 視窗操作。
- `try_10`（GET 單一圖片）需要資料庫裡有 `id=1` 的資料，可先跑 `try_11` 建立一筆。
- `try_18` 的辨識功能需要本機 AI 模型（單元六，`uv sync --extra ml`）。
