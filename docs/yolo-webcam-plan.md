# 計畫書：Webcam + YOLO 即時物件偵測整合

**狀態**：建議草案（供評估與教材規劃用，暫無實作排程）
**定位**：單元十（補充教材），承接單元六（AI 推論）、單元七（Redis）、單元八（樣板與靜態檔）
**前提**：延續本專案的教學取向——優先清楚示範單一觀念，註解密度高於一般專案

---

## 1. 目標與範圍

做出一個網頁：開啟使用者的攝影機，把畫面即時送到 FastAPI 後端跑 YOLO 物件偵測，
再把偵測框疊回畫面上。附帶一條單張圖片的偵測 API，讓既有的上傳流程也能用。

**做**

- 即時偵測網頁（WebSocket）與單張圖片偵測 API（HTTP）
- 偵測結果的儲存與查詢（沿用現有的 PostgreSQL 或 MongoDB）
- 沒裝 YOLO 相依套件時，其餘功能完全不受影響（優雅降級）

**不做**

- 物件追蹤（tracking，跨幀的 ID 關聯）、姿態估計、分割
- 自訂資料集訓練——用預訓練的 COCO 80 類就好，訓練不是這門課的主題
- 多路攝影機、錄影回放、GPU 叢集部署

---

## 2. 架構選擇（最重要的決定）

「攝影機在哪裡、推論在哪裡」有三種組合，先比較再選：

| 方案 | 攝影機來源 | 推論位置 | 傳輸 |
| --- | --- | --- | --- |
| A. 後端開攝影機 | 跑 FastAPI 的那台機器（`cv2.VideoCapture(0)`） | 後端 | MJPEG 串流回瀏覽器 |
| **B. 前端抓、後端推論**（建議） | 使用者的瀏覽器（`getUserMedia`） | 後端 | WebSocket 傳幀、回座標 |
| C. 純前端 | 使用者的瀏覽器 | 瀏覽器（onnxruntime-web） | 不傳 |

### 建議選 B，理由

**A 的架構是錯的示範。** `cv2.VideoCapture(0)` 抓的是「伺服器那台機器」上的攝影機。
教學現場老師在自己筆電上跑起來會很順，但學生一連上老師的機器，看到的是老師的鏡頭；
部署到雲端則根本沒有攝影機可開。而且 `VideoCapture` 是獨佔資源，第二個人連進來就搶不到。
它唯一的優點是程式碼最短（一個 `StreamingResponse` 加生成器就會動），適合當暖身
demo，但要明講限制，不能當成最終架構。

**C 不經過後端**，等於整堂 FastAPI 課在這個單元沒有戲份。可以在教材裡當作取捨的對照組
討論（延遲最低、伺服器零負擔，但模型與權重全部曝露給用戶端、換模型要重新部署前端）。
它在第 7 節的升級路徑裡會以「邊緣推論」的身分回歸——那時它是對的答案，只是不是這個
單元要教的。

**B 是三個方案中唯一「攝影機位置對、又輪得到 FastAPI 上場」的**，具體理由：

- **攝影機的位置沒有替代選項**。網頁應用取得使用者攝影機的唯一正規途徑就是瀏覽器的
  `getUserMedia`；A 的根本問題就是把攝影機放錯了邊，這不是實作品質能補救的。
- **算力與模型留在伺服器端**：模型私有（不像 C 整包下載到用戶端）、換模型或調參不必
  重新部署前端、弱裝置（手機、平板）也能享用完整精度的模型。這也是「AI 能力包成 API」
  這門課一以貫之的主題。
- **教學上剛好補到課程缺的兩塊**：WebSocket（雙向、長連線，與前面所有 HTTP 端點形成
  對照），以及「同步推論不阻塞事件迴圈」在串流下的真正難點——單張上傳時
  `run_in_threadpool` 一包就解決，串流才會遇到背壓與丟幀（見 4.3、4.4），
  是單元 6.7 的自然深化。

**同時要誠實標定 B 的等級**：它是「互動 demo 等級的近即時」，適合單一使用者、區網、
每秒解析 5~15 幀的場景。它的天花板是結構性的（不是調參能解的），天花板在哪、
超過之後架構要怎麼換，獨立成第 7 節詳述。

### B 的資料流

```
瀏覽器                                   FastAPI
------                                   -------
getUserMedia 取得 MediaStream
  └→ <video> 播放（原始畫面）
  └→ 每次迴圈：
       drawImage 到離屏 canvas（縮到長邊 640）
       canvas.toBlob('image/jpeg', 0.6)
       ws.send(blob)  ────────────────→  await ws.receive_bytes()
                                          ↓ 限制同時推論數（Semaphore）
                                          run_in_threadpool(detect, bytes)
                                          ↓ YOLO 推論
       onmessage ←────────────────────   ws.send_json({"boxes": [...]})
       用回傳的正規化座標畫 canvas 疊層
       ↓
       收到回應才送下一幀（in-flight = 1）
```

最後一行是整個設計的核心，見 4.4。

---

## 3. 檔案異動清單

全部比照現有慣例，不新增新的架構概念：

| 檔案 | 動作 | 說明 |
| --- | --- | --- |
| `app/services/yolo_service.py` | 新增 | 模型單例 + lazy import，比照 `ai_service.py` |
| `app/routes/detect.py` | 新增 | WebSocket + 單張偵測 + 網頁三條路由 |
| `app/templates/detect.html` | 新增 | Jinja2 + Bootstrap，比照 `upload.html` |
| `app/static/detect.js` | 新增 | 前端邏輯；目前 `static/` 只有 CSS，這支正好讓 8.5 的掛載有實際用途 |
| `app/main.py` | 修改 | `include_router(detect.router)` |
| `app/config.py` | 修改 | 加 `YOLO_MODEL`、`YOLO_CONF`、`YOLO_MAX_CONCURRENCY` |
| `pyproject.toml` | 修改 | 新增 `yolo` 可選依賴 |
| `.env.example` | 修改 | 對應的環境變數與註解 |
| `.gitignore` | 修改 | 加 `*.pt`（ultralytics 會自動下載權重到工作目錄） |
| `tests/test_smoke.py` | 修改 | 未安裝套件時 skip 的偵測測試 |
| `README.md` | 修改 | 可選依賴一節、單元十說明 |

要不要開新的 `routes/detect.py`、而不是塞進 `routes/ai.py`：建議開新的。`ai.py` 已經
兩百多行、涵蓋五個教材小節，而偵測這條線包含 WebSocket 與一個 HTML 頁面，性質跟
`ai.py` 裡清一色的「上傳一張圖回 JSON」不同。

---

## 4. 關鍵設計決策

### 4.1 依賴放 optional extra，且用 headless 版 OpenCV

```toml
# 單元十：YOLO 物件偵測
yolo = [
    "ultralytics>=8.3.0",
    "opencv-python-headless>=4.10.0",
]
```

- **一定要 `opencv-python-headless`，不要 `opencv-python`。** 後者帶 GUI 相依，伺服器端
  完全用不到 `imshow`，卻會在 Docker 裡因為缺 `libGL.so.1` 直接 ImportError——這個錯誤
  訊息跟 OpenCV 本身毫無關聯，會找很久。
- ultralytics 會拉 torch 進來，跟現有的 `ml` extra 重疊；兩個都裝不會衝突，但要在 README
  註明「`--extra yolo` 跟 `--extra ml` 一樣是大型下載」。
- **授權要註明**：ultralytics 是 AGPL-3.0。教學與自用沒問題，但學生日後拿去商用會踩到。
  文件裡寫一句，並提替代路線：把模型匯出成 ONNX、改用 `onnxruntime` 跑（推論程式碼要自己
  寫前後處理，教學成本較高，不列為主線）。

### 4.2 模型單例 + lazy import（照抄現有模式）

```python
# app/services/yolo_service.py
_model = None


def get_model():
    """模組級單例（教材 6.7）：避免每個請求都重新載入權重"""
    global _model
    if _model is None:
        from ultralytics import YOLO  # lazy import

        _model = YOLO(settings.YOLO_MODEL)  # 預設 yolov8n.pt
    return _model
```

跟 `ai_service.get_classifier()` 一模一樣的形狀。學生看過分類那一節之後，這裡不需要
再解釋一次，只需要指出「同一個模式又出現了」。

### 4.3 推論放 threadpool，而且要限制同時推論數

`run_in_threadpool` 這件事教材 6.7 已經教過，但**串流情境多了一個新問題**：單張上傳一次
只有一個請求，串流是每秒好幾幀連續灌進來。若每幀都無條件丟進 threadpool：

- Starlette 的 threadpool 預設 40 條執行緒，很快被塞滿；
- torch 本身在每條執行緒裡又會開多執行緒做矩陣運算，彼此搶 CPU，結果是**全部都變慢**；
- 佇列愈積愈長，使用者看到的框會落後畫面好幾秒（延遲雪崩）。

解法是加一個號誌，滿載時**直接丟棄這一幀**而不是排隊：

```python
_sem = anyio.Semaphore(settings.YOLO_MAX_CONCURRENCY)  # 預設 2

async def detect_or_drop(frame: bytes) -> list[dict] | None:
    """滿載時回 None（丟幀）——即時串流寧可少畫一幀，也不要積壓延遲"""
    if _sem.statistics().tasks_waiting > 0:
        return None
    async with _sem:
        return await run_in_threadpool(detect_frame, frame)
```

「即時系統寧可丟資料也不要積壓」是這一節最值得教的觀念，比 YOLO 本身重要。

### 4.4 前端用 in-flight = 1 的節流，不要固定 FPS

直覺寫法是 `setInterval(sendFrame, 100)` 固定 10 FPS。但後端在不同機器上的速度差很多
（見第 6 節），固定頻率不是送太少（畫面卡但 CPU 閒著）就是送太多（全靠後端丟幀）。

改成「**收到上一幀的結果，才送下一幀**」：

```js
async function loop() {
  if (!running) return;
  const blob = await grabFrame();      // 抓一幀並壓成 JPEG
  ws.send(blob);
  // 不在這裡 setTimeout；等 ws.onmessage 收到結果後再呼叫 loop()
}
```

這樣送幀速率會自動貼合後端的實際處理能力，快的機器自然跑得快，慢的機器也不會積壓。
概念上就是 TCP 的滑動視窗開到 1，簡單且不需要調參。

### 4.5 傳 binary JPEG，不要傳 base64

`canvas.toBlob(cb, 'image/jpeg', 0.6)` 拿到 Blob 直接 `ws.send(blob)`，後端
`await ws.receive_bytes()`。

- base64 會多 33% 體積，兩端還各要編解碼一次；WebSocket 原生支援二進位，沒有理由不用。
- 送出前把長邊縮到 640（YOLO 預設 `imgsz=640`），送更大的圖只是浪費頻寬——模型內部
  照樣會縮回去。640×480 的 JPEG（quality 0.6）大約 25~40 KB，10 FPS 約 3 Mbps，區網沒問題。

### 4.6 回傳正規化座標（0~1），不要回像素座標

後端收到的是「縮過的 640 寬圖」，前端 `<video>` 的顯示尺寸又是另一回事（還會隨視窗縮放、
CSS `object-fit` 變動）。回像素座標的話，前端要自己記住三組尺寸去換算，是這類專案最常見的
「框跑掉了」bug 來源。

後端統一除以推論圖的寬高再回傳：

```json
{
  "boxes": [
    {"label": "person", "conf": 0.91, "x1": 0.12, "y1": 0.08, "x2": 0.44, "y2": 0.95}
  ],
  "elapsed_ms": 82
}
```

前端只要乘上 canvas 的實際顯示寬高就好，視窗怎麼縮都不會歪。

### 4.7 優雅降級（專案的核心原則，不可破例）

- 沒裝 `--extra yolo`：`import ultralytics` 只在函式內發生，app 照常啟動，其他路由不受影響。
- 單張偵測 API：捕捉 `ImportError`，回 **503** 並附上安裝指令，不要讓它變成 500。
- WebSocket：連線建立後才發現模型載不起來時，先 `send_json({"error": ...})` 再關閉連線，
  不要無聲斷線——前端只會看到 `onclose`，完全不知道發生什麼事。
- 第一次呼叫會下載權重（yolov8n.pt 約 6 MB），若無網路要給明確錯誤訊息。

### 4.8 沿用既有的 Redis 與資料庫，不另起爐灶

- **單張偵測**可以完全比照 `/classify`：`image_hash(content)` 當快取 key，命中就直接回。
  即時串流則**不要快取**——每幀都不同，只會白白塞爆 Redis。
- **統計**：用 `cache_incr` 累計各類別出現次數（`stats:detect:person`），做一個小小的
  「今天看到幾個人」端點，剛好複習單元七。
- **儲存偵測結果**：MongoDB 比 PostgreSQL 適合——每張圖的框數量不定、欄位是巢狀結構，
  正是單元九示範 schema-free 的好例子。比照 `routes/mongo_demo.py` 的留言集合寫法。

### 4.9 資源保護

WebSocket 端點會直接吃 CPU，且目前專案的端點都沒有身分驗證。至少要：

- 限制單一訊息大小（超過 2 MB 直接丟棄並警告，避免有人拿 4K 圖猛灌）
- 限制同時連線數（例如 4 條，超過就拒絕並說明原因）
- 現有的 `rate_limit.py` 是為 HTTP 設計的，WebSocket 要另外處理（在 `accept()` 前檢查）

---

## 5. 分階段實作

每一階段都能獨立驗收，不必等全部做完才看得到東西。

**Phase 0：可行性確認（半小時）**
一支 `practices/try_19_yolo_local.py`，讀 `test_images/` 裡的圖跑一次偵測、印出結果與耗時。
確認套件裝得起來、權重下載得到、這台機器一幀要多久。**先量到數字再決定後面的節流參數。**

**Phase 1：單張圖片偵測 API**
`POST /api/v1/ai/detect`（multipart 上傳）→ 回 JSON。純 HTTP，沒有新概念，
把 `yolo_service.py` 的單例、threadpool、快取、優雅降級全部做對。可以用 `requests/api.http` 測。

**Phase 2：偵測結果畫在圖上**
`POST /api/v1/ai/detect-image` 回傳畫好框的 JPEG（`Response(content=..., media_type="image/jpeg")`）。
這一步是為了讓學生確認「座標是對的」，也順便示範回傳二進位內容。

**Phase 3：WebSocket 即時偵測（主線）**
`GET /detect` 網頁 + `WS /ws/detect`。前端 `getUserMedia` → canvas → WebSocket，
後端限流、丟幀、回正規化座標，前端 canvas 疊框。這一段是本單元的重點。

**Phase 4：結果落地與統計**
把偵測結果寫進 MongoDB、用 Redis 累計類別次數，加一個統計頁。

（**選配**：把方案 A 的 MJPEG 版本做成一支 30 行的 `practices/try_20_mjpeg_local.py`，
當作「為什麼不用這個架構」的教材對照，不要放進 app。）

---

## 6. 效能預期

先講清楚免得期待落空。`yolov8n`（最小的 nano 模型）、`imgsz=640`、單張：

| 環境 | 每幀耗時 | 實際可得 FPS |
| --- | --- | --- |
| Apple Silicon（MPS） | 30~60 ms | 15~30 |
| 一般桌機 CPU | 80~200 ms | 5~12 |
| 老舊筆電 CPU | 300 ms+ | 3 以下 |

- **不需要 GPU**，但 CPU 上就是這個數量級，教材裡要寫明，否則學生會以為自己做錯了。
- 想更快：`yolov8n` 已是最小，再快只能降 `imgsz`（例如 416）或改用 ONNX / OpenVINO 匯出。
- Phase 0 量到的數字，直接拿來設 `YOLO_MAX_CONCURRENCY`（CPU 核心數 ÷ 2 是合理起點）。

這個數量級就是方案 B 的架構天花板——想突破它不是調參問題，而是換架構的問題，見下一節。

---

## 7. 往高效能即時的升級路徑（何時該離開方案 B）

### 7.1 先定位：方案 B 到底是哪個等級

方案 B 是「互動 demo 等級的近即時」：單一使用者、區網、每秒解析 5~15 幀、
端到端延遲約 100~300 ms。要注意兩件讓它「比帳面數字好用」的事：

- 使用者看到的**原始畫面**是本機 `<video>` 直接播的 30/60 FPS，只有偵測框以解析頻率
  更新。體感是「流暢畫面 + 稍慢的框」，不是 5 FPS 的幻燈片。
- 很多掛著「即時解析」名字的需求——數人流、入侵偵測、物件計數——本質是**事件型**應用，
  每秒解析 5~10 幀綽綽有餘，根本不需要幀幀分析。

所以「即時」要先問清楚規格：如果答案是上面這種，B 就夠了；如果答案是
30 FPS 幀幀分析、延遲 < 100 ms、同時接多路攝影機、要跨幀追蹤——**那就不該用 B**，
而且不是把 B 調快，是換架構。

### 7.2 B 的天花板為什麼是結構性的

- **逐幀 JPEG 沒有幀間壓縮**。視訊編碼（H.264/VP8）靠前後幀差異壓縮，同畫質下頻寬
  約為逐幀 JPEG 的十分之一。B 等於放棄整個視訊編碼技術，在連續傳靜態圖。
- **in-flight = 1 是鎖步協定**。有效 FPS = 1000 ÷（RTT + 編碼 + 推論），任一項降不下來
  FPS 就上不去。把 in-flight 開大不是解法——那只是把 4.3 丟掉的積壓又搬回來。
  「不積壓」與「吞吐被延遲綁死」是同一個設計的兩面。
- **WebSocket 走 TCP**。掉一個封包，後面所有幀都得等重傳（head-of-line blocking）；
  在公網或 Wi-Fi 邊緣，延遲會突波。即時視訊的正規傳輸走 UDP，晚到的幀直接放棄。
- **Python + threadpool 是單路思維**。一路串流可以；十路攝影機同時進來，GIL 與
  CPU 排程都不是加執行緒能解決的。
- **沒有時間軸語意**。每幀獨立推論、沒有時間戳（PTS），做不了追蹤（tracking）、
  事件去重、跨幀平滑——真正的視訊分析功能都建立在時間軸上。

### 7.3 三階升級，每階都是「把一個平面從 FastAPI 抽走」

**第一階：WebRTC（aiortc）——換掉傳輸平面**

瀏覽器不再逐幀抓圖，改用 `RTCPeerConnection` 把攝影機的視訊軌整條送出
（瀏覽器做硬體 H.264/VP8 編碼）；伺服器用 aiortc 收軌、解碼取幀、跑推論，
結果經 DataChannel 回傳。

- 改變：傳輸從「JPEG over TCP」變成「視訊編碼 over UDP/SRTP」。頻寬降一個數量級、
  沒有 head-of-line blocking、傳輸延遲可壓到幾十 ms；伺服器還能自主決定取幀頻率，
  不再被往返時間鎖步。
- FastAPI 的角色：只剩 signaling（一條 HTTP 端點交換 SDP），媒體流不經過它。
- 代價：引入 ICE/STUN/TURN、SDP 協商、`MediaStreamTrack` 的非同步處理——這些是
  WebRTC 協定本身的複雜度，跟 FastAPI 的教學主題無關，所以本單元不走這條。
- 沒解決的事：推論仍在同一個 Python 行程裡，速度沒變快，多路擴展問題原封不動。

**第二階：媒體管線 + 推論伺服器分離——換掉運算平面**

正式量產的形狀。把「收流、解碼、推論」整段從 web 框架抽出來：

```
攝影機/瀏覽器 → 媒體管線（GStreamer / FFmpeg，硬體解碼 NVDEC）
                 → 推論伺服器（Triton + TensorRT，跨路批次）
                 → 結果進佇列（Redis Streams / Kafka）
前端 ←—— WebSocket/SSE 推播事件 ——— FastAPI（控制平面）
```

- 改變：解碼交給硬體、推論跨路批次（batching 讓 GPU 吃飽）、偵測結果變成佇列裡的
  事件流。NVIDIA DeepStream 就是「媒體管線 + 推論」這一整段的現成品。
- FastAPI 的角色：純控制平面——開關串流、查詢結果、認證、對外 API。
  **完全不碰原始視訊**，而這恰好是它擅長的事。
- 該升到這一階的訊號：要接多路攝影機、要 GPU 吞吐、要做追蹤與跨幀事件邏輯。

**第三階：邊緣推論——把運算搬離伺服器**

模型放到裝置端（瀏覽器 onnxruntime-web / WebGPU、手機 CoreML / TFLite、
攝影機內建 NPU），只把偵測事件與必要的縮圖送回伺服器。方案 C 在這裡以正確的
身分回歸——它不適合當教學主線，但在「延遲至上」的規格下是對的答案。

- 改變：延遲最低（推論不過網路）、伺服器負擔趨近於零、離線也能作動。
- FastAPI 的角色：收事件、彙整統計、發布模型版本。
- 代價：模型與權重曝露在用戶端、裝置算力參差、模型更新要走部署流程。
- 實務常見混合式：邊緣先粗篩（「有沒有人」），命中的片段才送伺服器精算。

### 7.4 對照表

| | 方案 B（本計畫） | 一階：WebRTC | 二階：管線分離 | 三階：邊緣推論 |
| --- | --- | --- | --- | --- |
| 端到端延遲 | 100~300 ms | < 100 ms | 視管線設計，可 < 100 ms | < 50 ms |
| 解析 FPS | 5~15（被 RTT 鎖步） | 受推論限制，不受 RTT 鎖步 | 30+，跨路批次 | 視裝置算力 |
| 多路擴展 | 差 | 差（推論未動） | 好（核心目的） | 天生分散 |
| 跨幀功能（追蹤等） | 無 | 可做（有連續幀） | 完整（DeepStream 內建） | 視裝置 |
| 建置複雜度 | 低 | 中 | 高 | 中～高 |
| FastAPI 的角色 | 媒體 + 推論 + API | signaling + API | 控制平面 | 事件彙整 |

一句話總結：**方案 B 不是通往高效能即時的第一步，而是教學上最短的路**。真要往上走，
方向不是「把 B 調快」，而是逐階把媒體平面、運算平面從 web 框架抽走——最後 FastAPI
剩下的，恰好是它最擅長的控制平面。這個「知道自己在哪一階、下一階長什麼樣」的判斷，
本身就值得寫進教材當一節討論。

---

## 8. 已知的坑

**`getUserMedia` 只在安全上下文可用。** `http://localhost` 算安全，但 `http://192.168.x.x`
**不算**——學生拿手機連老師機器的區網 IP，攝影機會直接拿不到，而且錯誤訊息很不明顯。
解法：`uvicorn --ssl-keyfile/--ssl-certfile` 自簽憑證，或用 cloudflared / ngrok 開臨時
HTTPS 通道。這件事一定要寫進教材，不然示範現場會卡住。

**`--reload` 開發模式下改任何檔案都會重載模型**，每次要等好幾秒。跑這個單元時建議
`uv run uvicorn app.main:app`（不加 `--reload`），或接受它。

**權重檔會下載到工作目錄**，記得 `.gitignore` 加 `*.pt`，別讓 6 MB 的檔案進版控。

**Windows 上第一次 import ultralytics 特別慢**（torch 的 DLL 載入），不是當掉。

**WebSocket 在 `TimingMiddleware` 底下的行為**：`BaseHTTPMiddleware` 不處理 WebSocket
連線，現有的計時中介軟體不會攔到 `/ws/detect`，所以 log 裡不會有它的紀錄——這是預期行為，
但值得在教材裡點一句，免得學生以為 log 壞了。

---

## 9. 測試

- `tests/test_smoke.py` 加 `pytest.importorskip("ultralytics")`，未安裝時整組 skip，
  維持核心 `uv sync` 下 `pytest -q` 全綠的前提。
- 單張偵測：用 `test_images/` 的圖，斷言回傳結構與座標範圍在 0~1 之間（不斷言類別，
  模型版本一換就會壞）。
- WebSocket：`TestClient.websocket_connect` 送一幀、收一則回應即可。
- **未安裝時的降級路徑要有測試**：呼叫 `/api/v1/ai/detect` 應該回 503 而不是 500，
  這比偵測準不準更重要——它是全專案的設計原則。

---

## 10. 待確認

1. **教材編號**：掛成「單元十」還是「單元六的延伸（6.8）」？影響 docstring 的對照標記。
2. **YOLO 版本**：`yolov8n` 最穩、資料最多；`yolo11n` 較新較準但教學資源少。建議 v8。
3. **結果要不要落地**（Phase 4）？只做即時顯示的話範圍會小很多。
4. **是否需要方案 A 的 MJPEG 對照組**，或教材裡用文字說明取捨就夠。
