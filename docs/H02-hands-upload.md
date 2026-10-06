# H02：單張圖片上傳偵測

> 教材 附錄 D「MediaPipe 進階：串流與瀏覽器端推論」的實作說明，三篇之一。
> 後端的基礎（Tasks API、單例、優雅降級）在教材 8.7。

對應頁面 `app/static/demos/H02-hands-1.html`
（啟動後開 <http://localhost:8000/static/demos/H02-hands-1.html>），端點 `POST /api/v1/hands/upload`。

一句話：**瀏覽器把一張圖用 multipart/form-data 傳給後端，後端存檔、偵測、寫進資料庫，
把 21 個關鍵點的正規化座標回傳，骨架由前端自己畫。**

這是三頁裡最單純的一種 —— 一次請求一次回應，沒有連線狀態要維護。
先把這一頁的資料流搞懂，再看 [H03](H03-hands-ws.md) 的串流版本會輕鬆很多。

---

## 涉及的檔案

| 檔案 | 負責什麼 |
|---|---|
| `app/static/demos/H02-hands-1.html` | 選檔／拍照、送出請求、畫骨架 |
| `app/routes/hands.py` | 端點、上傳檢查、存檔、寫資料庫 |
| `app/services/hand_landmark.py` | 模型載入、圖片解碼、推論 |
| `app/models/image.py` | `images` 資料表，偵測結果存在 `ai_result` 欄位 |
| `app/main.py` | 啟動時載入模型、掛載 `/uploads` 靜態目錄 |

---

## 整體流程

```
瀏覽器                                          FastAPI                      MediaPipe
  |                                                |                             |
  |  (a) 選檔 or 拍照 → Blob                        |                             |
  |  (b) URL.createObjectURL(blob) → <img> 先顯示   |                             |
  |                                                |                             |
  |  (c) POST /api/v1/hands/upload                 |                             |
  |      Content-Type: multipart/form-data         |                             |
  |      欄位 file = <JPEG bytes>                  |                             |
  |----------------------------------------------->|                             |
  |                                                | (d) 檢查 MIME / 大小        |
  |                                                | (e) 模型就緒？否則 503      |
  |                                                | (f) run_in_threadpool ----->| 解碼 + 推論
  |                                                |                             | (約 27 ms)
  |                                                |<----------------------------|
  |                                                | (g) 存圖檔 uploads/xxx.jpg  |
  |                                                | (h) 存 uploads/xxx.json     |
  |                                                | (i) INSERT images           |
  |<-----------------------------------------------|                             |
  |  (j) JSON：座標 + 檔名 + 尺寸                   |                             |
  |  (k) 依座標在 <canvas> 上畫骨架                 |                             |
```

關鍵在於：**影像只往後端送一次，座標只往前端送一次**，之後前端要怎麼畫是前端的事。
後端從頭到尾沒有產生任何「畫好骨架的圖片」。

---

## 前端：把圖變成請求

### 兩種來源，同一條路

選檔與拍照最後都收斂到同一個 `detectBlob(blob, filename)`：

```js
// 選檔：input[type=file] 的 files[0] 本身就是 File（File 是 Blob 的子類別）
my_file.addEventListener('change', function () {
    if (!my_file.files.length) return;
    detectBlob(my_file.files[0]);
});
```

拍照這條要多做兩步 —— 影片畫面本身不是檔案，要先鏡射畫進 canvas 再壓成 JPEG：

```js
const shot = document.createElement('canvas');
shot.width = my_video.videoWidth;      // 攝影機的實際解析度
shot.height = my_video.videoHeight;    // 不是 <video> 被 CSS 縮成多大

const shotCtx = shot.getContext('2d');
shotCtx.scale(-1, 1);                  // 左右鏡射
shotCtx.translate(-shot.width, 0);
shotCtx.drawImage(my_video, 0, 0);

shot.toBlob(blob => detectBlob(blob, 'webcam.jpg'), 'image/jpeg', 0.9);
```

`videoWidth` 與 CSS 寬度是兩回事，用錯的話拍出來的照片會是被縮小過的模糊版本。
`toBlob` 是非同步的，壓縮完成才會呼叫回呼函式。

**鏡射的兩個理由**（H03、H04 完全一樣的處理）：自拍視角要跟照鏡子一樣；
以及 MediaPipe 判定 Left／Right 時假設輸入影像已經鏡射過，
直接存原始的前鏡頭畫面，左右手標籤會全部相反。

`<video>` 預覽那邊也有一行 CSS `transform: scaleX(-1)`，讓瞄準時看到的方向跟拍下來一致。
但**那只是顯示效果**，canvas 這邊不另外鏡射的話，存下來的像素仍然是沒鏡射的原圖。

選檔上傳的那條路**不做鏡射** —— 那是既有的照片，不是自拍畫面，鏡射反而會弄錯。

### 組出 multipart 請求

```js
const fd = new FormData();
fd.append('file', blob, filename || blob.name);

fetch('/api/v1/hands/upload', { method: 'POST', body: fd })
```

三個容易踩的點：

1. **欄位名一定要是 `file`**，因為後端的參數就叫 `file`：
   `async def upload_and_detect(session: SessionDep, file: UploadFile = File(...))`。
   名字對不上，FastAPI 會回 422（欄位缺失），而不是什麼有意義的錯誤。
2. **`append` 的第三個參數是檔名**。省略的話瀏覽器會送出 `"blob"`，
   後端 `os.path.splitext()` 取不到副檔名，存檔就會變成 `.bin`。
3. **不要自己設 `Content-Type`**。把 `FormData` 直接交給 `fetch`，
   瀏覽器會自動加上 `multipart/form-data; boundary=----WebKitFormBoundary...`。
   手動寫死 header 反而會少掉 boundary，後端直接解析失敗。

### 預覽與記憶體

```js
if (previewUrl) URL.revokeObjectURL(previewUrl);
previewUrl = URL.createObjectURL(blob);
my_img.src = previewUrl;   // 不等後端回應就先顯示
```

`createObjectURL` 產生的 `blob:` 網址會一直握著那份資料，換圖時不 `revoke` 就會累積。
這裡先顯示預覽再送出請求，使用者不必等網路來回才看到自己選了什麼。

---

## 後端：三層防線

`app/routes/hands.py` 把檢查拆成幾個小函式，每一層擋的是不同的東西。

### 第一層：模型在不在

```python
def _check_model_ready() -> None:
    if not hand_landmark.is_ready():
        raise HTTPException(503, hand_landmark.unavailable_reason())
```

回 **503（服務暫時不可用）而不是 500**，是刻意的：套件沒裝或模型檔不存在是「外部資源沒準備好」，
不是程式寫錯。這跟 `database.get_session()` 連不到資料庫時回 503 是同一套語意。

`mediapipe` 在這個專案是可選依賴（`uv sync --extra mediapipe`），所以模型沒載入有兩種原因：
套件沒裝，或模型檔不見了。`unavailable_reason()` 會回對應的那一句，訊息裡直接帶著該跑的指令。

模型在 `app/main.py` 的 lifespan 啟動時就載入，不是每個請求載一次 ——
建立 detector 要花一百多毫秒，逐請求建立等於每次都白付這個成本。

### 第二層：上傳內容合不合法

```python
async def _read_upload(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_TYPES:      # jpeg / png / webp
        raise HTTPException(415, f"不支援的格式：{file.content_type}")
    if file.size is not None and file.size > MAX_SIZE:
        raise HTTPException(413, "檔案過大（超過 10 MB）")
    content = await file.read()
    if len(content) > MAX_SIZE:                     # 讀完再量一次
        raise HTTPException(413, "檔案過大（超過 10 MB）")
    return content
```

**為什麼要量兩次大小**：`file.size` 來自用戶端送來的標頭，可能沒有、也可能造假。
先用它做快速攔截（省下讀取的成本），真的讀完之後再量一次才算數。

### 第三層：圖片解不解得開

```python
try:
    return await run_in_threadpool(hand_landmark.detect, content)
except (OSError, PILImage.DecompressionBombError) as exc:
    raise HTTPException(400, f"無法解析圖檔：{exc}")
```

MIME 型別只是個標頭，把 `.exe` 改名成 `.jpg` 一樣送得出來。真正的把關是 Pillow 打不打得開：
打不開會丟 `OSError`（`UnidentifiedImageError` 是它的子類別），
壓縮炸彈（幾 KB 的檔案解開後是幾萬 x 幾萬的圖）會丟 `DecompressionBombError`。

**`run_in_threadpool` 不是可選的**。`detect()` 是純 CPU 的阻塞工作，
直接在 async 函式裡呼叫會卡住整個事件迴圈 —— 那 30 毫秒之內，
所有其他請求（包括完全無關的端點）全都不會被處理。

---

## 推論：`hand_landmark.py` 做了什麼

### 解碼的四個步驟，一個都不能少

```python
img = PILImage.open(BytesIO(content))
img = ImageOps.exif_transpose(img)     # 依 EXIF 轉正
img = img.convert("RGB")               # 統一成三通道
source_width, source_height = img.size # 轉正之後才是使用者看到的尺寸
if max(img.size) > settings.HAND_MAX_SIDE:
    img.thumbnail((max_side, max_side))
rgb = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))
```

| 步驟 | 不做會怎樣 |
|---|---|
| `exif_transpose` | 手機照片常常是「橫著存、靠 EXIF 標記轉正」。瀏覽器顯示時會自動套用這個標記，後端不套的話，模型看到的是躺著的圖，偵測率很差，而且回傳的座標跟前端看到的畫面對不起來 |
| `convert("RGB")` | 灰階（L）、透明（RGBA）、調色盤（P）都不是三通道，`mp.Image` 的 SRGB 格式只吃三通道 |
| `thumbnail` | 8000x6000 的圖推論會很慢。因為回傳的是正規化座標，縮圖完全不影響座標意義 |
| `ascontiguousarray` | `mp.Image` 會把陣列的記憶體位址直接交給 C 函式，要求記憶體連續的 uint8 |

第一項是前後端溝通的關鍵：**兩邊都要套 EXIF，座標才對得上。**

### 為什麼用單例加鎖

```python
_detector: HandLandmarker | None = None
_lock = threading.Lock()

with _lock:
    result = _detector.detect(mp_image)
```

H02 是「一張圖一個請求」，沒有跨影格的狀態要維護，所以全站共用一個 detector 就好。
`run_in_threadpool` 會把工作丟到不同執行緒，而 MediaPipe 從未保證 detector 可以被
多執行緒同時呼叫，所以用一把鎖把推論串成一次一個。

這個設計到了 H03 就**不能用了** —— 原因見 [H03 的說明](H03-hands-ws.md#重點二為什麼不能共用-h02-的單例)。

---

## 存檔：圖與 JSON 同主檔名

```python
result = await _detect(content)        # 先偵測

ext = os.path.splitext(file.filename or "")[1] or ".bin"
if ext.lower() == ".json":             # 副檔名剛好是 .json 的話，JSON 檔會把圖檔蓋掉
    ext = ".bin"
stem = uuid.uuid4().hex                # 圖與 JSON 共用的主檔名
new_name = f"{stem}{ext}"              # abc123....jpg
json_name = f"{stem}.json"             # abc123....json
```

**先偵測再存檔**：圖檔壞掉的話直接回 400，不會在 `uploads/` 留下垃圾檔案。

**檔名用 UUID 而不是原檔名**：原檔名可能重複（大家都叫 `IMG_0001.jpg`）、
可能夾帶路徑穿越（`../../etc/passwd`）、可能是中文而在某些檔案系統上出問題。
原檔名另外存在資料庫的 `title` 欄位與 JSON 的 `original_name`，資訊不會遺失。

JSON 檔多帶了幾個檔案層面的欄位，單獨拿出來看也知道對應哪張圖：

```json
{
  "original_name": "webcam.jpg",
  "filename": "d45ba76f12404b7e92d12ef39bbd6c55.jpg",
  "mime_type": "image/jpeg",
  "file_size": 67719,
  "width": 640, "height": 960,
  "processed_width": 640, "processed_height": 960,
  "model": "hand_landmarker",
  "mediapipe_version": "1.0.0",
  "hand_count": 2,
  "hands": [ ... ]
}
```

`ensure_ascii=False` 是必要的，否則中文原檔名會被寫成 `\uXXXX` 跳脫字串。

同一份結果也寫進資料庫的 `images.ai_result`（`app/models/image.py` 早就預留的 JSON 欄位）。
結果裡帶了 `model` 與 `mediapipe_version`，之後接別的 AI 功能時才分得出這筆資料是誰產生的。

---

## 回應格式

```json
{
  "id": 4,
  "original_name": "webcam.jpg",
  "filename": "d45ba76f12404b7e92d12ef39bbd6c55.jpg",
  "url": "/uploads/d45ba76f12404b7e92d12ef39bbd6c55.jpg",
  "json_filename": "d45ba76f12404b7e92d12ef39bbd6c55.json",
  "json_url": "/uploads/d45ba76f12404b7e92d12ef39bbd6c55.json",
  "width": 640,
  "height": 960,
  "processed_width": 640,
  "processed_height": 960,
  "model": "hand_landmarker",
  "mediapipe_version": "1.0.0",
  "hand_count": 2,
  "hands": [
    {
      "index": 0,
      "handedness": "Left",
      "score": 0.9361,
      "landmarks": [
        {"x": 0.39257, "y": 0.7065, "z": -0.0},
        {"x": 0.34296, "y": 0.75028, "z": -0.01981}
      ]
    }
  ]
}
```

| 欄位 | 說明 |
|---|---|
| `id` | 這筆資料在 `images` 表的主鍵，之後可以用 `GET /api/v1/images/{id}` 查回來 |
| `width` / `height` | 原圖尺寸，**已套用 EXIF 轉正**。前端拿它換算像素座標 |
| `processed_width` / `processed_height` | 實際送進推論的尺寸。大圖會先被縮小，但因為座標是正規化的，不影響前端怎麼畫 |
| `handedness` | `Left` 或 `Right`。**以「鏡像後的影像」為基準判定**，所以拍照前要先鏡射（見上面） |
| `landmarks` | 21 個點。`x`／`y` 是 0~1 的正規化座標，`z` 是相對於手腕的深度（越小離鏡頭越近） |

`/uploads` 在 `app/main.py` 有掛成靜態目錄，所以 `url` 與 `json_url` 都可以直接用瀏覽器開。

### 21 個點的編號

```
索引 0     手腕
索引 1~4   拇指（由掌心往指尖）
索引 5~8   食指
索引 9~12  中指
索引 13~16 無名指
索引 17~20 小指
```

---

## 前端：從座標畫回骨架

### 先判斷成功失敗

```js
.then(r => r.json().then(body => ({ ok: r.ok, body })))
.then(({ ok, body }) => {
    if (!ok) {
        my_status.textContent = `錯誤：${body.detail}`;
        return;
    }
    ...
})
```

`fetch` **不會**因為 4xx／5xx 就進 `catch`（只有網路層失敗才會），所以一定要自己看 `r.ok`。
FastAPI 的 `HTTPException` 回的是 `{"detail": "..."}`，
不先判斷就直接讀 `body.hand_count` 只會拿到 `undefined`。

### canvas 的解析度與顯示尺寸要分開想

```js
my_canvas.width = result.width;      // 內部解析度 = 原圖尺寸
my_canvas.height = result.height;
```

CSS 那邊是 `position: absolute; inset: 0; width: 100%; height: 100%`，
讓 canvas 縮放到跟 `<img>` 一樣大。**內部解析度用原圖、顯示大小交給 CSS**，
線條在放大縮小時都不會糊掉。

### 正規化座標換算

```js
const points = hand.landmarks.map(p => ({
    x: p.x * result.width,
    y: p.y * result.height,
}));
```

這就是正規化座標的好處：後端可能把圖縮到 1280 才推論，前端可能顯示成 400 寬，
兩邊解析度完全不同也不必換算，各自乘上自己的尺寸就對了。

線寬也跟著圖片大小走，小圖才不會被粗線蓋住：

```js
const unit = Math.max(result.width, result.height) / 200;
```

---

## 常見問題

**Q：為什麼骨架的位置歪掉了？**
多半是 EXIF 沒對上。確認後端的 `exif_transpose` 有跑到，
而且前端是用 `result.width/height`（後端回的轉正後尺寸）在乘，不是用 `<img>` 的顯示尺寸。

**Q：左右手標籤好像反了？**
MediaPipe 假設輸入影像已經鏡射過。拍照那條路已經在 canvas 上鏡射過了，
標籤應該是對的；如果還是反的，先確認鏡射是做在 canvas 上，而不是只有 `<video>` 的 CSS。

**選檔上傳**的情況不一樣：那是既有照片，方向取決於當初怎麼拍的。
如果那張照片本身是沒取消鏡像的自拍，標籤就會相反 —— 這是照片的問題，不是程式的。

**Q：`hand_count` 是 0，但畫面上明明有手。**
沒偵測到手不算錯誤，會正常回 `hand_count: 0`、`hands: []`。
先確認光線是否足夠、手是否完整入鏡。門檻在
`hand_landmark.py` 的 `min_hand_detection_confidence`（預設 0.5），調低比較敏感、也比較容易誤判。

**Q：想只偵測不存檔？**
`app/routes/hands.py` 還有一個 `POST /api/v1/hands/detect`，
只回座標、不存檔也不寫資料庫。改一下前端的 fetch 網址就能切換。

---

## 怎麼自己驗

不開瀏覽器也能測：

```sh
curl -X POST http://localhost:8000/api/v1/hands/upload \
     -F "file=@某張有手的照片.jpg;type=image/jpeg"
```

或用 `requests/api.http`（VS Code 的 REST Client 外掛）裡「8.7 MediaPipe」那兩段。

---

## 接下來

- [H03](H03-hands-ws.md)：同樣是後端推論，但改成 WebSocket 連續串流，重點在回壓控制
- [H04](H04-hands-live.md)：同一個模型改在瀏覽器裡跑，影像完全不離開本機
