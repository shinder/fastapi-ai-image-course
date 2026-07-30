# 計畫書：MediaPipe 手部關鍵點標示（單張圖片上傳）

**狀態**：建議草案（供評估與教材規劃用，暫無實作排程）
**定位**：單元六的延伸（6.8 候選），承接 6.3／6.4（推論端點）、6.7（threadpool）、7.5（快取）、8.5（靜態檔）
**前提**：延續本專案的教學取向——優先清楚示範單一觀念，註解密度高於一般專案

---

## 1. 目標與範圍

使用者上傳一張圖片，後端用 MediaPipe 偵測手部的 21 個關鍵點，把骨架標示畫回圖上，
再連同座標一起回應給使用者。

**做**

- 單張圖片的手部標示 API（回座標 JSON + 標好的圖片 URL）
- 同一份推論結果的第二種回應型別（直接回 PNG 二進位），示範回應型別的取捨
- 一個 Jinja2 上傳頁，看得到標示結果（比照 `routes/web.py` 的 PRG 模式）
- 沒裝 MediaPipe 或沒下載模型檔時，其餘功能完全不受影響（優雅降級）

**不做**

- 手勢辨識（Gesture Recognizer 是另一個 task，靠 landmark 再往上做一層分類）
- 攝影機即時串流——那是 `yolo-webcam-plan.md` 的主題，兩份計畫的架構問題不同
- 姿態（Pose）、臉部（Face Mesh）、整體（Holistic）等其他 MediaPipe task
- 3D 重建。`z` 只當相對深度看，本計畫的繪圖是純 2D

---

## 2. 回應形式的選擇（最重要的決定）

MediaPipe 的呼叫本身很短，這個 pipeline 真正需要決定的是**「標示完成後回什麼」**——
它會往回決定要不要存檔、能不能快取、前端怎麼接。四種形式：

| 方案 | 回應內容 | 優點 | 缺點 |
| --- | --- | --- | --- |
| A. 只回座標 JSON | 21 個 landmark 的正規化座標 | 資料可再利用（存 DB、算手勢）；後端不必畫圖 | 前端得自己用 canvas 疊圖才看得到 |
| B. 只回圖片 | `Response(media_type="image/png")` | `<img src>` 直接指過去就看得到 | 座標丟失、無法存 DB、不能同時回其他欄位 |
| **C. JSON + 圖片 URL**（建議） | `{"hands": [...], "annotated_url": "..."}` | 兩者兼得；圖片走 `StaticFiles`，能被瀏覽器快取 | 要處理產出檔的存放與清理 |
| D. JSON + base64 | data URI 內嵌在 JSON 裡 | 單一請求、免存檔 | 體積膨脹 33%、無法快取、大圖讓 JSON 很肥 |

### 建議 C 當主線，另做一條 B 當對照

**A 不夠。** 使用者的需求是「標示完成後再回應」，只回座標等於把最後一哩路推給前端。
但 A 的核心資產——座標——必須保留，所以它不是被否決，而是被 C 包含。

**B 單獨用不行，當變體很好。** 回二進位圖時整個 response body 就是圖，沒有地方再放
`count`、`elapsed_seconds` 或錯誤說明；「沒偵測到手」這種情況也只能回一張沒畫東西的原圖，
使用者無從分辨是沒有手、還是偵測失敗。但它作為**第二條端點**很有教學價值：同一份推論結果、
兩種回應型別，正好對照單元三講過的 `Response`。

**D 不建議。** 教材裡塞一段 base64 看起來很方便（免存檔、免處理靜態路徑），但會讓學生
誤以為這是回傳圖片的正規做法。實務上它只適合「圖很小且絕不重複使用」的場合。

**C 的另一個好處是快取變得自然**：產出檔用圖片內容的 hash 命名，同一張圖上傳兩次會落在
同一個檔名，第二次連畫都不用畫，直接回同一個 URL（見 4.7）。

### C 的資料流

```
POST /api/v1/ai/hand-landmarks   (multipart: file)
  │
  ├─ 1. 驗證           content_type 白名單 + 大小上限（沿用 images.py 的 ALLOWED_TYPES）
  │
  ├─ 2. 讀取與前處理    content = await file.read()
  │                     PIL 開檔 → ImageOps.exif_transpose() → convert("RGB")
  │                     長邊縮到 1280（見 4.5）
  │
  ├─ 3. 查快取         digest = image_hash(content)      ← 沿用 cache_service 現成的
  │                     Redis 有座標 且 annotated 檔還在 → 直接跳到 6
  │
  ├─ 4. 推論           run_in_threadpool(detect_hands, img)      ← 同步，必須包
  │                     → [{handedness, score, landmarks: [{x,y,z} ×21]}, ...]
  │
  ├─ 5. 繪製與存檔      正規化座標 ×(width, height) → 像素座標
  │                     PIL ImageDraw 畫 21 點 + 21 條骨架線
  │                     存成 uploads/annotated/{digest}.png（檔名用 hash → 天然去重）
  │                     座標 JSON 寫進 Redis（TTL 3600）
  │
  └─ 6. 回應           {"hands": [...], "count": n,
                         "annotated_url": "/uploads/annotated/{digest}.png",
                         "elapsed_seconds": 0.04, "cached": false}
```

第 5 步的檔名決定了第 3 步能不能成立，這是整個設計裡唯一需要繞一下的地方。

---

## 3. 檔案異動清單

全部比照現有慣例，不新增新的架構概念：

| 檔案 | 動作 | 說明 |
| --- | --- | --- |
| `app/services/hand_service.py` | 新增 | 模型單例 + lazy import + PIL 繪圖，比照 `ai_service.py` / `ocr_service.py` |
| `app/routes/ai.py` | 修改 | 加 2 條端點（JSON 版、圖片版） |
| `app/routes/web.py` | 修改 | 加 `GET /web/hand`、`POST /web/hand` 上傳頁（選配，Phase 3） |
| `app/templates/hand.html` | 新增 | 比照 `upload.html`，Bootstrap + 結果顯示（選配） |
| `app/config.py` | 修改 | 加 `HAND_MODEL_PATH`、`HAND_MAX_NUM`、`ANNOTATED_SUBDIR` |
| `pyproject.toml` | 修改 | 新增 `hand` 可選依賴 |
| `.env.example` | 修改 | 對應的環境變數與註解 |
| `models/.gitkeep` | 新增 | 模型檔存放目錄，比照 `uploads/.gitkeep` 的慣例 |
| `.gitignore` | 修改 | 加 `models/*.task`（模型權重不進版控） |
| `requests/api.http` | 修改 | 兩條端點的呼叫範例 |
| `tests/test_smoke.py` | 修改 | 未安裝套件時 skip 的偵測測試 + 降級路徑測試 |
| `README.md` | 修改 | 可選依賴一節、模型檔下載說明 |

**不開新的 router。** 這點跟 `yolo-webcam-plan.md` 的結論相反，理由也正好相反：手部標示
就是「上傳一張圖、回 JSON」，跟 `ai.py` 現有的 `/classify`、`/ocr`、`/describe` 完全同型，
沒有 WebSocket 也不需要獨立的網頁架構。`ai.py` 目前 230 行，加兩條端點還在可讀範圍內。

---

## 4. 關鍵設計決策

### 4.1 依賴放 optional extra，但要先講清楚它會拖進來什麼

```toml
# 單元 6.8：MediaPipe 手部關鍵點
hand = [
    "mediapipe>=0.10.21",
]
```

**下限刻意設在 0.10.21，而不是最新的 1.0.0**——那是最後一個提供 Intel Mac wheel 的版本
（見下方平台限制）。這樣有新 wheel 的平台會自動解到 1.0.0，Intel Mac 則自然落回 0.10.21，
學生不必手動指定版本。Tasks API 在 0.10.21 已經存在，本計畫的程式碼兩邊都適用。
（uv 的 universal lock 會為不同平台分岔解析，理論上成立，但 Phase 0 要在 Intel Mac 上
實際驗證一次；若不如預期，退路是 README 註明手動 `uv pip install "mediapipe==0.10.21"`。）

MediaPipe 的相依清單（1.0.0 實際查得）是 `absl-py`、`certifi`、`numpy`、`flatbuffers`、
`matplotlib`、`sounddevice`、**`opencv-contrib-python`**。三件事要寫進教材：

- **無法換成 headless 版 OpenCV。** `yolo-webcam-plan.md` 4.1 的結論是「一定要用
  `opencv-python-headless`，否則 Docker 裡缺 `libGL.so.1`」——但 MediaPipe 把
  `opencv-contrib-python`（GUI 版）寫成硬相依，我們無從指定。要進 Docker 的話只能反過來做：
  在映像檔裡補系統套件（Debian 系是 `libgl1` 與 `libglib2.0-0`）。這是本專案第一個
  「相依套件替我們做了選擇」的案例，值得當一節討論。
- **會多裝 `sounddevice` 與 `matplotlib`**。前者是 MediaPipe 音訊 task 用的，我們完全用不到，
  但它需要系統的 PortAudio 才 import 得起來。Phase 0 要確認在乾淨環境下 `import mediapipe`
  會不會因此失敗（若會，就得在文件註明系統套件）。
- **體積比 `--extra ml` 小得多**。不含 torch，整包約數百 MB 而非數 GB，README 的可選依賴
  表格裡可以標明這點——這也是選 MediaPipe 而非 torch 系方案的實際好處。

**平台限制（必須寫進 README，否則教學現場會卡住）**：mediapipe 1.0.0 只提供
macOS arm64、Linux x86_64／aarch64、Windows amd64／arm64 的 wheel，**沒有 Intel Mac
（macOS x86_64）版**。最後一個有 Intel Mac wheel 的是 **0.10.21**——上面把依賴下限設在這一版就是為了這件事。
若解析仍失敗（Phase 0 要驗證），錯誤訊息不會告訴學生這是平台問題，README 得直接寫明
「Intel Mac 請用 `uv pip install "mediapipe==0.10.21"`」。

### 4.2 用 Tasks API，不用 legacy 的 `mp.solutions`

兩套 API 都能做手部偵測：

| | `mp.solutions.hands`（舊） | `mediapipe.tasks.python.vision`（新） |
| --- | --- | --- |
| 模型檔 | 內含，不必下載 | 要自己下載 `.task` 檔 |
| 繪圖 | 附 `drawing_utils.draw_landmarks()`，一行畫完 | 沒有，要自己畫 |
| 狀態 | legacy，官方文件已不再更新 | 現行建議 |

**建議選新的，即使它多兩件麻煩事。** 舊 API 的三行示範對教材很誘人，但教學專案給學生
淘汰中的 API 是負債；而且「自己畫」在這裡不是純負擔——正規化座標換算成像素座標
（見 4.5、4.6）本身就是這一節最該教的東西，`draw_landmarks()` 一行帶過反而把它藏起來了。

```python
# app/services/hand_service.py
_landmarker = None
_lock = threading.Lock()


def get_landmarker():
    """模組級單例（教材 6.7）：避免每個請求都重新載入模型"""
    global _landmarker
    if _landmarker is None:
        from mediapipe.tasks import python as mp_python  # lazy import
        from mediapipe.tasks.python import vision

        _landmarker = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=settings.HAND_MODEL_PATH
                ),
                running_mode=vision.RunningMode.IMAGE,  # 單張圖，非串流
                num_hands=settings.HAND_MAX_NUM,
            )
        )
    return _landmarker
```

形狀跟 `ai_service.get_classifier()`、`ocr_service.get_reader()` 一致。學生看過前兩節之後，
這裡不需要再解釋一次單例，只要指出「同一個模式第三次出現」。

### 4.3 模型檔要自己下載，缺檔時回 503 並附上指令

Tasks API 需要 `hand_landmarker.task`（float16 版約 7 MB）：

```
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

放 `models/hand_landmarker.task`，`.gitignore` 加 `models/*.task` 並保留 `models/.gitkeep`
（比照專案現有的 `uploads/.gitkeep`、`test_images/.gitkeep` 慣例，讓目錄本身進版控）。
**開檔前先檢查存在性**，
缺檔就回 503 並把下載指令寫進錯誤訊息本身：

```python
if not os.path.exists(settings.HAND_MODEL_PATH):
    raise HTTPException(503, f"缺少模型檔，請執行：curl -o {settings.HAND_MODEL_PATH} {MODEL_URL}")
```

讓學生看到 `FileNotFoundError` 的堆疊、自己去 Google 模型檔網址，是可以避免的挫折。
這也延續了專案「不可用時給明確訊息，而不是 500」的原則。

（不建議做「首次呼叫自動下載」——那會讓第一個請求無聲卡住十幾秒，且在無網路的教學環境
失敗得更難懂。明確的手動步驟比隱藏的魔法適合教材。）

### 4.4 推論放 threadpool，而且單例要上鎖

`run_in_threadpool` 教材 6.7 已經教過，照用：

```python
results = await run_in_threadpool(detect_hands, img)
```

**但這裡多一件 `/classify` 沒有的事：`HandLandmarker` 不保證 thread-safe。**
`run_in_threadpool` 會讓併發請求同時打到同一個模組級單例；`transformers` 的 pipeline
大致撐得住，MediaPipe 的 IMAGE-mode landmarker 併發呼叫 `detect()` 則可能出現偶發的
座標錯亂或崩潰——而且是低機率、難重現的那種，正式環境才會遇到。

```python
def detect_hands(img: Image.Image) -> list[dict]:
    import mediapipe as mp  # lazy import
    import numpy as np

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.array(img))
    with _lock:  # MediaPipe 的 landmarker 非執行緒安全，序列化推論
        result = get_landmarker().detect(mp_image)
    ...
```

單張只要幾十毫秒，序列化的排隊成本可以接受。替代做法是 thread-local 各持一個實例
（吞吐較好，但每條執行緒都吃一份模型記憶體）。**教材選 Lock 版**：程式碼短、觀念單一，
並在註解裡點出另一條路。這一節的可教點是「模組級單例 + threadpool 併發 = 要想一下
thread safety」，前兩節剛好沒踩到，這裡補上。

### 4.5 前處理三件事：EXIF、縮圖、共用同一個影像物件

```python
img = Image.open(BytesIO(content))
img = ImageOps.exif_transpose(img)        # 一定要，見下
img = img.convert("RGB")
img.thumbnail((1280, 1280))               # 長邊縮到 1280
```

- **EXIF 方向不處理會整個歪掉。** 手機拍的照片實際像素常是橫的，靠 EXIF Orientation
  旗標轉正。少了 `exif_transpose()`，MediaPipe 吃到的是未轉正的圖，畫出來的骨架會歪掉
  或標到空白處——最麻煩的是你在檔案總管裡看原圖是正的（看圖軟體幫你轉了），
  完全不會聯想到 EXIF。現有的 `ocr_service` 也有同樣議題，可以一併提。
- **縮圖省時間也省記憶體**，而且因為 landmark 是正規化座標（0~1），縮圖**不影響**回傳的
  座標值——這點值得在教材裡明講，它是正規化座標的直接好處。
- **推論與繪圖必須用同一個 PIL 物件。** 若先縮圖推論、再拿原圖來畫，乘出來的像素座標
  雖然比例對得上（正規化座標的功勞），但兩張圖的尺寸不同會讓線寬與點半徑的視覺比例走鐘；
  更糟的情況是有人改成「原圖推論、縮圖繪製」，混用就會錯。教材裡固定成一個變數，
  從頭到尾只有 `img`。

### 4.6 繪圖用 PIL，自己定義骨架連線

專案已經依賴 Pillow（`ocr_service` 就用它讀圖），不必為了畫線再引入 cv2 的繪圖 API
（雖然 MediaPipe 已經把 opencv 拖進來了，見 4.1）。手部的 21 條連線寫成模組級常數：

```python
# 21 個 landmark 的骨架連線（MediaPipe 手部拓樸）
HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),              # 拇指
    (0, 5), (5, 6), (6, 7), (7, 8),              # 食指
    (5, 9), (9, 10), (10, 11), (11, 12),         # 中指
    (9, 13), (13, 14), (14, 15), (15, 16),       # 無名指
    (13, 17), (17, 18), (18, 19), (19, 20),      # 小指
    (0, 17),                                     # 手腕到小指根，掌部收口
)
```

繪圖時把正規化座標乘上實際寬高：

```python
w, h = img.size
pts = [(lm["x"] * w, lm["y"] * h) for lm in hand["landmarks"]]   # z 畫 2D 時忽略
for a, b in HAND_CONNECTIONS:
    draw.line([pts[a], pts[b]], fill=(0, 255, 0), width=2)
for x, y in pts:
    draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 0, 0))
```

- 線寬與點半徑**建議按圖片尺寸縮放**（例如 `max(2, w // 400)`），否則 1280 寬的圖上
  2px 的線細到看不清，400 寬的小圖上又粗到蓋住手指。
- 多隻手時**每隻手換一個顏色**，並在手腕點旁標 `handedness`，這樣「偵測到兩隻手」
  在圖上是看得出來的。

### 4.7 快取：座標存 Redis，圖檔用 hash 當檔名

比照 `/classify` 的做法（教材 7.5），但因為要回一張圖，快取分成兩半：

```
cache:ai:hand:{digest}        → 座標 JSON（Redis，TTL 3600）
uploads/annotated/{digest}.png → 標好的圖（檔案系統，無 TTL）
```

`digest` 直接用 `cache_service.image_hash(content)`，現成的。**產出檔用內容 hash 命名，
就順便得到了去重**：同一張圖上傳兩次會落在同一個檔名，第二次連畫都不用畫。

命中判定要**兩邊都check**：Redis 有座標、但檔案被手動刪掉了（或 Redis 有資料而
`uploads/` 被清空），就得重畫。這比只看 Redis 多一次 `os.path.exists`，但少了它會回一個
404 的 `annotated_url`，而且錯得很安靜。

不要把圖片本身塞進 Redis。二進位圖進 Redis 要編碼、佔記憶體，而檔案系統加上
`StaticFiles` 已經是更好的圖片快取層（還附帶 HTTP 快取標頭）。

**清理策略**：`uploads/annotated/` 會單向長大。教材階段不做自動清理（講清楚就好），
但要在文件裡寫明這是刻意的取捨，並提一句正式環境的做法（cron 掃 mtime、或改存物件儲存
搭配生命週期規則）。

### 4.8 產出檔放 `uploads/annotated/`，不要放頂層

看起來只是選個目錄，但頂層會出兩個問題：

- **`web.py` 的 `gallery()` 會把標註圖全部列出來。** 它用 `os.listdir(UPLOAD_DIR)` 加副檔名
  過濾掃描頂層，標註圖進去會混在使用者上傳的圖片列表裡。放子目錄則因為目錄名沒有副檔名，
  被現有的過濾條件自然排除，`gallery()` 一行都不用改。
- **原圖與衍生檔混在一起就分不開了**，之後想做清理（4.7）會很難寫。

**不需要再 mount 一個 `StaticFiles`。** `main.py` 已經掛了 `/uploads`，它涵蓋子目錄，
`/uploads/annotated/xxx.png` 直接就能取用。這點值得在教材裡點一句——學生常以為每個子目錄
都要各掛一次。

順帶一個安全性檢查：`digest` 是我們自己算出來的十六進位字串，不是使用者可控的檔名，
所以這條路徑**不需要**經過 `images.py` 的 `safe_upload_path()`。但教材裡要說明為什麼不需要
（來源可信），免得學生以為路徑穿越的防護可以隨便省略。

### 4.9 不需要背景任務——判斷依據是延遲量級

`ai.py` 裡的 `/generate-async` 用了 `BackgroundTasks` + Redis 任務狀態（教材 7.10），
自然會有人問手部標示要不要照做。**不要。** MediaPipe 單張偵測是幾十毫秒等級，
直接同步回應就好；包成背景任務只會讓使用者為了一個 40 毫秒的工作多送一次輪詢請求。

這剛好是個對照案例，值得寫成教材的一小段：**該不該用背景任務，看的是延遲量級
（幾秒 vs 幾十毫秒）與外部依賴（要不要跨網路呼叫別人的 API），不是「有沒有跑 AI」。**
`/generate` 要等 OpenAI 數秒，所以需要；`/classify`、`/ocr`、手部標示都不需要。

### 4.10 優雅降級（專案的核心原則，不可破例）

- 沒裝 `--extra hand`：`import mediapipe` 只在函式內發生，app 照常啟動，其他路由不受影響。
- 端點層捕捉 `ImportError` → **503** 並附安裝指令，不要變成 500。
- 缺模型檔 → **503** 並附下載指令（4.3）。
- Redis 掛掉 → `cache_get` 回 `None` 視為未命中，照樣推論、照樣回應（`cache_service` 已保證）。
- `uploads/annotated/` 不存在 → `os.makedirs(exist_ok=True)`，比照 `web.py` 的做法。

現有的 `/classify` 其實是讓 `ImportError` 冒出去變成 500 的（`ai.py` 沒有 try）。
這份計畫建議新端點做到 503，並**順手把 `/classify`、`/ocr` 一起補上**——否則專案裡會有
兩種不一致的降級行為，教材上更難解釋。這件事列進第 8 節待確認，因為它動到既有端點。

### 4.11 邊界情況

- **沒偵測到手**：回 **200** 加 `{"hands": [], "count": 0}`，`annotated_url` 回原圖（或 `null`）。
  不要回 404——請求是成功的，只是結果為空。這是 REST 語意的常見錯誤，值得在教材點名。
- **多隻手**：`num_hands` 預設 2，以 `Form` 參數讓學生調，觀察調成 1 時另一隻手消失。
- **`handedness` 在自拍鏡頭下會反過來**。MediaPipe 判斷左右手的前提是「影像未鏡像」，
  而前鏡頭預覽通常是鏡像的。教材要標一句，這是最常見的困惑點之一——學生會以為模型錯了。
- **圖片很大**：4.5 的 `thumbnail` 已經處理推論成本，但仍要在端點層擋檔案大小上限
  （沿用 `images.py` 的作法），避免有人上傳 4K 圖佔滿記憶體。
- **非圖片內容**：MIME 白名單 + PIL 開檔失敗回 400，不要讓 `UnidentifiedImageError` 變 500。

---

## 5. 分階段實作

每一階段都能獨立驗收，不必等全部做完才看得到東西。

**Phase 0：可行性確認（半小時）**
一支 `practices/try_19_mediapipe_hand.py`：讀一張手部照片跑一次偵測，印出手數、
21 個座標與耗時。要確認的是——這台機器裝不裝得起來（4.1 的平台限制）、乾淨環境下
`import mediapipe` 會不會因 `sounddevice` 失敗、模型檔下載得到、單張實際幾毫秒。
**先量到數字，再決定 4.4 要不要真的上鎖、README 的效能表怎麼寫。**
順便要準備一張測試用的手部照片放 `test_images/`（現有的 `cat.jpg`、`text.png` 派不上用場），
並比照現有慣例在 `.gitignore` 開白名單。

**Phase 1：JSON 版端點（主線）**
`POST /api/v1/ai/hand-landmarks` → 回座標 + `annotated_url`。
`hand_service.py` 的單例、Lock、threadpool、EXIF、縮圖、繪圖、快取、優雅降級全部做對。
用 `requests/api.http` 驗收。這一步做完，整個 pipeline 就成立了。

**Phase 2：圖片版端點（對照組）**
`POST /api/v1/ai/hand-landmarks/preview` → 直接回 PNG 二進位
（`Response(content=..., media_type="image/png")`）。
共用同一個 service 函式，只換回應型別——教材上正好拿來講「同一份結果、兩種回應」的取捨。

**Phase 3：網頁版（選配）**
`GET /web/hand` 表單頁、`POST /web/hand` 處理上傳並顯示結果，比照 `web.py` 的 PRG 模式。
這一步讓非技術使用者也能操作，也讓單元八的樣板與 8.5 的靜態檔掛載多一個實際用途。

**Phase 4：結果落地（選配，範圍會明顯變大）**
把座標寫進 MongoDB（每張圖手數不定、landmark 是巢狀陣列，正是單元九 schema-free 的
好例子），加一條查詢端點。**不建議放進第一版**——它跟手部標示本身沒有必然關係，
`mongo_demo.py` 已經示範過同樣的觀念。

---

## 6. 效能預期

MediaPipe 的手部模型很小（float16 約 7 MB），是 CPU 導向設計，**不需要 GPU**。
下面的數量級是預期值，Phase 0 要用實測數字取代：

| 項目 | 預期 |
| --- | --- |
| 首次載入模型（單例初始化） | 0.1~0.5 秒 |
| 單張偵測（1280 長邊，CPU） | 20~60 毫秒 |
| 繪圖 + 存 PNG | 10~30 毫秒 |
| 快取命中 | 個位數毫秒（不推論、不繪圖） |

跟 `--extra ml` 的 ViT 分類（每張數百毫秒到數秒、模型數百 MB）比，這是完全不同的量級——
教材可以拿這組對比說明「模型大小與任務複雜度決定架構」：同樣是影像推論，
一個需要考慮快取與非同步，一個同步回應就綽綽有餘。

第一次呼叫會比後續慢（載模型），跟 `/ocr` 端點一樣的現象；`/ocr` 已經在回應裡放了
`elapsed_seconds`，這裡照做，學生自己就能觀察到。

---

## 7. 已知的坑

**Intel Mac 裝不起來。** mediapipe 1.0.0 沒有 macOS x86_64 wheel，最後一版是 0.10.21。
`uv sync --extra hand` 會解析失敗，訊息不會指出是平台問題。README 必須寫明退路。
（見 4.1；這是本計畫最可能在教學現場爆掉的一點。）

**EXIF 方向。** 見 4.5。列在這裡是因為它的症狀（骨架歪掉／標到空白處）跟原因（EXIF）
之間的距離最遠，最花時間。

**`opencv-contrib-python` 是硬相依，Docker 會缺 `libGL.so.1`。** 見 4.1。
本地開發不會遇到，一進容器就爆，而且錯誤訊息跟 OpenCV 看不出關聯。

**併發下的偶發錯亂。** 見 4.4。單人測試永遠不會遇到，壓測或正式環境才出現。
若 Phase 0 之後決定不上鎖，這一條要留在文件裡當已知風險。

**`--reload` 下改任何檔案都會重載模型。** 這裡影響比 YOLO 那份小（模型才 7 MB、
載入不到半秒），但仍會在 log 裡多出一次載入，教材可以順口提一句。

**`num_hands` 調大不會變準。** 它是上限而非目標，設 4 不會讓兩隻手的圖偵測出四隻手，
但會增加後處理成本。學生常誤解這個參數。

**MediaPipe 會印一堆 INFO 級的原生 log**（TFLite delegate 之類），首次載入時看起來像
錯誤訊息。不是壞了，但值得在教材裡預告一句。

---

## 8. 測試

- `tests/test_smoke.py` 加 `pytest.importorskip("mediapipe")`，未安裝時整組 skip，
  維持核心 `uv sync` 下 `pytest -q` 全綠的前提。
- **降級路徑的測試比偵測結果的測試更重要**（它是全專案的設計原則）：
  - 未安裝 mediapipe 時呼叫端點 → 斷言 **503**，不是 500。
  - 模型檔不存在時 → 斷言 **503** 且訊息含下載網址。
- 有手的圖：斷言 `count >= 1`、每隻手 `len(landmarks) == 21`、所有 `x`／`y` 落在 0~1 之間、
  `annotated_url` 指到的檔案真的存在。**不要斷言具體座標值**——模型版本一換就會壞。
- 沒有手的圖（現有的 `cat.jpg` 剛好可用）：斷言 200 且 `count == 0`，這條測的是 4.11 的
  REST 語意決定。
- 圖片版端點：斷言 `content-type` 是 `image/png` 且 body 前幾個 byte 是 PNG magic number。
- 快取：同一張圖連送兩次，第二次 `cached` 為 true（Redis 不可用時這條要 skip，
  比照現有測試對 Redis 的處理）。

---

## 9. 待確認

1. **教材編號**：掛成 6.8，還是跟 YOLO 那份一起收進「單元十 補充教材」？影響 docstring 的
   對照標記。傾向 6.8——它跟 6.3／6.4 是同型端點，放在一起學生比較容易看出模式重複。
2. **要不要順手統一 `/classify`、`/ocr` 的 `ImportError` → 503**（見 4.10）？
   這會動到既有端點與既有教材段落，需要教材作者決定。
3. **Phase 3（網頁）與 Phase 4（MongoDB 落地）要不要納入第一版**？只做 Phase 1+2 的話，
   範圍大約是一支 service（100 行上下）加兩條端點。
4. **`uploads/annotated/` 的清理**：教材階段就講清楚不做（4.7），或提供一支手動清理腳本？
5. **要不要一併示範 Gesture Recognizer**（在 landmark 上再做手勢分類）？
   它能讓範例更有成果感，但會多一個模型檔與一層概念，可能該獨立成一節。
6. **測試圖片的授權**：需要一張可進版控的手部照片（比照 `cat.jpg`／`text.png` 的處理），
   要確認來源授權允許放進公開 repo。
