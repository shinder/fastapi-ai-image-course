# H03：WebSocket 串流即時偵測

> 教材 附錄 D「MediaPipe 進階：串流與瀏覽器端推論」的實作說明，三篇之二。
> 後端的基礎（Tasks API、單例、優雅降級）在教材 8.7。

對應頁面 `src/my_fastapi/static/demos/H03-hands-ws.html`
（啟動後開 <http://localhost:8080/static/demos/H03-hands-ws.html>），端點 `WS /api/v1/hands/ws`。

一句話：**瀏覽器開一條 WebSocket，把攝影機影格連續壓成 JPEG 送給後端，
後端每收一格回一則座標 JSON，同時只讓一格在路上飛。**

跟 [H02](H02-hands-upload.md) 的差別不只是「換個傳輸協定」。
連線是持續的，就多出三個 H02 完全不必處理的問題：
**連線的資源生命週期、多連線的平行度、以及塞車時怎麼辦**。
最後一項（backpressure，回壓）是這一課真正的重點。

---

## 涉及的檔案

| 檔案 | 負責什麼 |
|---|---|
| `src/my_fastapi/static/demos/H03-hands-ws.html` | 攝影機、送影格、回壓控制、畫骨架 |
| `src/my_fastapi/routes/hands_ws.py` | WebSocket 端點、連線數上限、資源回收 |
| `src/my_fastapi/services/hand_stream.py` | 每條連線一個 detector、VIDEO 模式推論 |
| `src/my_fastapi/config.py` | `HAND_WS_MAX_CONN`（預設 4） |

注意 H03 **沒有**沿用 `src/my_fastapi/services/hand_landmark.py` 的單例 detector，
只沿用了它的 `decode_image()`。理由見下面。

---

## 整體流程

```
瀏覽器                                       FastAPI                    每連線的 detector
  |                                             |                              |
  |  (a) getUserMedia → <video>                 |                              |
  |  (b) new WebSocket(.../hands/ws)            |                              |
  |-------------------- 握手 ------------------->|                             |
  |                                             | (c) accept()                 |
  |                                             | (d) 連線數滿了？ → 1008 關閉  |
  |                                             | (e) 建 detector（threadpool）->| VIDEO 模式
  |<------------- {"type":"ready"} -------------|                              |
  |                                             |                              |
  |  (f) 畫面鏡射 → 480x360 JPEG                 |                             |
  |  (g) inFlight = true，送出 binary frame      |                             |
  |------------------ 二進位訊框 --------------->|                             |
  |                                             | (h) 解碼 + detect_for_video ->| 約 17 ms
  |                                             |<-----------------------------|
  |<----------- {"type":"result", ...} ---------|                              |
  |  (i) inFlight = false → 立刻送下一格          |                             |
  |      （回到 f，形成循環）                     |                             |
  |                                             |                              |
  |  (j) 使用者按停止 → ws.close()               |                              |
  |-------------------------------------------->| (k) finally：關 detector      |
  |                                             |     連線名額還回去            |
```

畫面更新（`requestAnimationFrame`）是**獨立於這個循環**的另一條迴圈，
用最後一次收到的結果重畫。所以後端只回得動 15 fps 時，影像本身仍然流暢。

---

## 重點一：回壓（backpressure）

### 錯誤的做法

直覺會想這樣寫：

```js
// 不要這樣寫
setInterval(() => {
    sendCanvas.toBlob(blob => ws.send(blob), 'image/jpeg', 0.5);
}, 50);   // 每 50 毫秒送一格 = 20 fps
```

只要後端處理的速度跟不上這個節奏（網路慢、伺服器忙、同時有別人在用），
影格就會在 WebSocket 的送信佇列裡**無上限累積**。
`ws.send()` 不會因為送不出去就報錯，它只是把資料排進佇列。

結果是：畫面上的骨架對應的是三秒前的手，而且**永遠追不回來** ——
因為累積的速度是固定的，佇列只會愈來愈長。這是即時串流最典型的失敗模式。

### 正確的做法：in-flight 固定為 1

```js
let inFlight = false;

function sendFrame() {
    if (!running || inFlight) return;          // 路上還有一格就不送
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // ...把畫面鏡射畫進 sendCanvas...

    inFlight = true;
    sentAt = performance.now();
    sendCanvas.toBlob(blob => {
        if (!running || !ws || ws.readyState !== WebSocket.OPEN) {
            inFlight = false;
            return;
        }
        ws.send(blob);
    }, 'image/jpeg', SEND_QUALITY);
}
```

送出的節奏由「後端多快回覆」決定，**完全不需要計時器**：

```js
if (msg.type === 'result') {
    lastResult = msg;
    inFlight = false;    // 路上空了
    updateStats(msg);
    sendFrame();         // 立刻送下一格，形成循環
}
```

第一格由 `ready` 訊息觸發，之後就是「收到 → 送出 → 收到 → 送出」的自我驅動循環。

這樣做的效果：**後端愈慢，前端送得就愈慢，延遲自動穩定在「一個來回」**。
系統會自己找到平衡點，不需要調整任何參數。實測在本機是 52 fps／來回 19 ms。

`toBlob` 的回呼裡要再檢查一次連線狀態，因為壓縮是非同步的 ——
這中間使用者可能已經按了停止。

### 為什麼不是 in-flight 2 或 3

允許多格在路上可以稍微提高吞吐（趁後端在算的時候先把下一格送上路），
代價是延遲變成兩三個來回。即時追蹤要的是低延遲不是高吞吐，所以固定為 1 最合適。
這個取捨值得自己動手改改看、觀察數字的變化。

---

## 重點二：為什麼不能共用 H02 的單例

`src/my_fastapi/services/hand_stream.py` 讓**每條連線各自建一個 detector**。
這跟 H02 的「全站一個單例 + 一把鎖」是相反的設計，有兩個原因。

### 正確性

```python
running_mode=RunningMode.VIDEO
```

VIDEO 模式的 detector 內部有跨影格的追蹤狀態（這也是它比 IMAGE 快的原因），
而且 `detect_for_video()` 要求時間戳**嚴格遞增**。

兩條連線交錯呼叫同一個 detector，時間戳會忽前忽後，MediaPipe 直接丟 `ValueError`；
就算時間戳沒問題，A 的追蹤狀態也會被 B 的影格汙染。

### 效能

共用單例加鎖，會把所有連線的推論串成一列。實測數字：

| 做法 | 結果 |
|---|---|
| 共用單例 + Lock | 全站上限約 35 fps（所有人一起分） |
| 每連線一個 detector（1 條） | 54 fps |
| 每連線一個 detector（2 條） | 每條 51 fps |
| 每連線一個 detector（4 條） | 每條 45.8~49 fps |
| 每連線一個 detector（8 條） | 每條 31 fps |

到 4 條都還幾乎線性擴展。代價是每條連線都吃一份模型記憶體與原生執行緒 ——
所以**一定要設連線數上限**。

### 時間戳由伺服器產生

```python
ts = time.monotonic_ns() // 1_000_000
if ts <= self._last_ts:
    ts = self._last_ts + 1
self._last_ts = ts
```

不採用用戶端送來的時間戳，因為用戶端的時鐘可能回撥、也可能亂送，
而只要有一格不遞增，`detect_for_video()` 就會丟例外讓整條連線斷掉。

用了單調時鐘還要再夾一次 `max(ts, last + 1)`，是防止同一毫秒內連續處理兩格 ——
推論夠快的時候真的會發生。

---

## 重點三：連線的生命週期

```python
_active_connections = 0

@router.websocket("/ws")
async def hands_ws(websocket: WebSocket):
    global _active_connections
    await websocket.accept()

    if _active_connections >= settings.HAND_WS_MAX_CONN:
        await websocket.send_json({"type": "error", "message": "連線數已達上限..."})
        await websocket.close(code=1008)
        return

    _active_connections += 1
    session = None
    try:
        session = await run_in_threadpool(HandStreamSession)
        ...
    except WebSocketDisconnect:
        pass
    finally:
        _active_connections -= 1
        if session is not None:
            await run_in_threadpool(session.close)
```

幾個設計決定：

**先 accept 再判斷連線數**，是為了能送一則看得懂的訊息給前端。
若在 accept 之前就 close，瀏覽器只會拿到一個沒有原因的握手失敗，除錯很痛苦。

**計數器不必上鎖**。asyncio 是單執行緒的，「檢查 → 加一」中間沒有任何 `await`，
不會被其他協程插隊。（真的會跑到別的執行緒的 `run_in_threadpool` 才需要小心。）

**`finally` 是必要的，不是保險**。少了它，斷線幾次之後名額就用光、
再也連不進來，而且每次斷線都漏掉一份模型記憶體與執行緒。

**建 detector 要丟 threadpool**。行程內第一次建立要初始化 GL 與 XNNPACK，約 170 毫秒。
不丟 threadpool 的話，這段時間整個伺服器的其他請求全部被卡住。

**關閉碼**：`1008` 是 policy violation，語意上就是「你沒違反協定，但我不接受」；
`1011` 是伺服器端出了狀況（沒裝 `mediapipe`、找不到模型檔）。

**沒裝 `mediapipe` 也不能讓 app 起不來**。它在這個專案是可選依賴，
所以 `hand_stream.py` 跟 `hand_landmark.py` 一樣只在函式內 import：
`HandStreamSession()` 建構時才會真的去載入套件，沒裝就丟 `ImportError`，
路由把它轉成一則 `error` 訊息再以 1011 關閉。這就是 WebSocket 版的優雅降級 ——
HTTP 端點回 503，WebSocket 沒有狀態碼可用，改用「訊息 + 關閉碼」表達同一件事。

---

## 訊息協定

### 用戶端 → 伺服器

只有一種：**二進位訊框，內容是 JPEG 的位元組**。沒有任何包裝。

```js
sendCanvas.toBlob(blob => ws.send(blob), 'image/jpeg', 0.5);
```

直接送 `Blob`，WebSocket 會當成二進位訊框，不必自己轉 `ArrayBuffer`。

**為什麼不用 base64**：base64 會讓體積多 33%，兩邊還要各多一次編解碼。
WebSocket 本來就支援二進位訊框，沒有理由再包一層。

伺服器端用 `receive()` 而不是 `receive_bytes()`，才能同時處理斷線與非影格訊息：

```python
message = await websocket.receive()
if message["type"] == "websocket.disconnect":
    break
frame = message.get("bytes")
if frame is None:
    continue     # 不是二進位訊框就不是影格，略過
```

### 伺服器 → 用戶端

三種 JSON 文字訊息，都有 `type` 欄位：

```json
{"type": "ready", "max_connections": 4, "active_connections": 1}
```

前端要**等到 `ready` 才開始送影格**，否則第一格會在 detector 還沒建好時就送到，白白排隊。

```json
{
  "type": "result",
  "seq": 42,
  "width": 480, "height": 360,
  "infer_ms": 16.9,
  "hand_count": 1,
  "hands": [
    {
      "handedness": "Left",
      "score": 0.936,
      "landmarks": [{"x": 0.3926, "y": 0.7065}, ...]
    }
  ]
}
```

```json
{"type": "error", "message": "無法解析影格：..."}
```

單一格解碼失敗**不會斷線**，回報一下就繼續等下一格。
只有連線數超限、沒裝 `mediapipe`、找不到模型檔這三種情況才會關閉連線。

### 跟 H02 的回應差在哪

| | H02 | H03 |
|---|---|---|
| `z` 座標 | 有 | 沒有（畫 2D 骨架用不到） |
| 小數位數 | 5 位 | 4 位 |
| `model` / `mediapipe_version` | 每次都送 | 不送（每格重複送是浪費） |
| 單格大小 | 約 3 KB | 約 1.4 KB |

一隻手 21 個點，每格省下的位元組乘上 20 fps 就很可觀。串流的每一個欄位都要問「值得嗎」。

---

## 影格尺寸與品質

```js
const SEND_WIDTH = 480;
const SEND_HEIGHT = 360;
const SEND_QUALITY = 0.5;
```

480x360 品質 0.5 大約 12 KB，20 fps 下約 240 KB/s。

**再往上加只是浪費頻寬，推論速度不會變。** 這是最反直覺的一點：

| 送進去的尺寸 | 推論時間 |
|---|---|
| 640x480 | 16.9 ms |
| 320x240 | 17.3 ms |

因為模型內部本來就會把圖縮到 192／224 像素。降解析度**只省頻寬，不省 CPU**。

順帶一提：如果看到影格大小只有 1~2 KB，多半是攝影機給的是全黑畫面
（鏡頭被遮住、或 macOS 系統層沒給瀏覽器相機權限）——純黑的 JPEG 壓完就是這麼小。

---

## 鏡射：一定要在送出之前做

```js
sendCtx.save();
sendCtx.scale(-1, 1);
sendCtx.translate(-SEND_WIDTH, 0);
sendCtx.drawImage(my_video, 0, 0, SEND_WIDTH, SEND_HEIGHT);
sendCtx.restore();
```

兩個理由：

1. 自拍視角要跟照鏡子一樣，抬右手時畫面右邊要動。
2. **MediaPipe 判定 Left／Right 時假設輸入影像已經鏡射過。**
   直接送原始的前鏡頭畫面過去，左右手標籤會全部相反。

第二點是重災區：只用 CSS 的 `transform: scaleX(-1)` 鏡射「顯示」是**不夠的** ——
那只影響畫面上看起來的樣子，模型看到的仍然是原始像素。

顯示用的 canvas 也要用同一個方向鏡射，座標才對得上：

```js
ctx.save();
ctx.scale(-1, 1);
ctx.translate(-my_canvas.width, 0);
ctx.drawImage(my_video, 0, 0, my_canvas.width, my_canvas.height);
ctx.restore();
```

---

## 兩張 canvas，各司其職

| canvas | 尺寸 | 內容 | 用途 |
|---|---|---|---|
| `sendCanvas`（離螢幕） | 480x360 | 只有鏡射後的影像 | 壓成 JPEG 送出去 |
| `my_canvas`（畫面上） | 640x480 | 鏡射影像 + 骨架 | 給人看 |

**不能只用一張**。畫面上那張已經畫了骨架，送過去等於讓模型去看自己上一格畫的線。

座標換算也因此變得很自然：後端拿到的是 480x360、前端顯示的是 640x480，
但因為回傳的是 0~1 的正規化座標，前端只要乘上**自己的** canvas 尺寸就好：

```js
const points = hand.landmarks.map(p => ({
    x: p.x * my_canvas.width,
    y: p.y * my_canvas.height,
}));
```

---

## 顯示迴圈與網路迴圈是分開的

```js
function loop() {
    if (!running) return;
    // 每一格畫面都重畫影像
    ctx.save(); ctx.scale(-1, 1); ctx.translate(-my_canvas.width, 0);
    ctx.drawImage(my_video, 0, 0, my_canvas.width, my_canvas.height);
    ctx.restore();
    // 骨架用「最後一次收到的結果」
    if (lastResult) draw(lastResult);
    requestAnimationFrame(loop);
}
```

`requestAnimationFrame` 跟著螢幕更新率跑（通常 60 或 120 Hz），
遠快於網路來回。骨架會有一格左右的延遲，但影像本身完全流暢。

如果把畫面更新綁在「收到結果」上，後端一慢畫面就會卡頓 —— 明明攝影機還好好的。

---

## 統計數字怎麼看

頁面上的五個 badge：

| badge | 意義 |
|---|---|
| `fps` | 每秒完成幾個來回。這是**端到端**的速率，不是攝影機的 fps |
| `來回 ms` | 從送出到收到結果。含網路 + JPEG 編碼 + 排隊 + 推論 |
| `伺服器推論 ms` | 後端 `detect_for_video()` 本身花的時間 |
| `影格 KB` | 這一格 JPEG 的大小 |
| `隻手` | 這一格偵測到幾隻手 |

**「來回」減掉「伺服器推論」就是傳輸與編碼的成本**，本機大約 2~3 毫秒。
拿這個數字跟 [H04](H04-hands-live.md) 的純本機延遲對照，正是這三頁要教的東西。

fps 的計算有個容易忽略的地方：分頁切到背景時 `requestAnimationFrame` 會停住
（瀏覽器正常的省電行為），中間會空出好幾秒的大洞，一起拿去平均會把數字算歪，
所以超過一秒的間隔就把舊資料丟掉重算。

---

## 常見問題

**Q：按了開始，畫面是黑的但 fps 有在跑。**
攝影機給的是全黑影格。依可能性排查：macOS 系統設定 → 隱私權與安全性 → 相機
是否有開放給瀏覽器（**這種情況網站權限會顯示已授權、track 也是 live，但畫面全黑**，
而不是報錯）；鏡頭是否被實體遮住；是否有其他 App 佔用。
最快的區分方法是開 Photo Booth 看看。

**Q：`WebSocket connection failed`。**
先確認伺服器有起來、而且是改動後啟動的。頁面是 https 時要用 `wss://`：

```js
const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
ws = new WebSocket(`${scheme}//${location.host}/api/v1/hands/ws`);
```

寫死 `ws://` 在 https 頁面上會被瀏覽器擋掉（mixed content）。

**Q：第五個人連不進來。**
這是設計如此，上限在 `HAND_WS_MAX_CONN`（預設 4）。要調高的話請先想清楚
每條連線都吃一份模型記憶體與一組原生執行緒，8 條時每人只剩 31 fps。

**Q：攝影機開不起來。**
`getUserMedia` 只在安全環境（HTTPS 或 localhost）可用。
用區網 IP 開這一頁會失敗，要用 cloudflared 開 HTTPS 通道（教材 4.5）。

---

## 怎麼自己驗

WebSocket 沒辦法用 `requests/api.http`（REST Client）測，用 Python 直接連
（`websockets` 套件已經隨 `fastapi[all]` 裝進來了，不必另外安裝）：

```python
import asyncio, json, websockets
from PIL import Image
import io

img = Image.open("某張有手的照片.jpg").convert("RGB").resize((480, 360))
buf = io.BytesIO(); img.save(buf, "JPEG", quality=50)
frame = buf.getvalue()

async def main():
    async with websockets.connect("ws://localhost:8080/api/v1/hands/ws") as ws:
        print(json.loads(await ws.recv()))       # {"type": "ready", ...}
        for _ in range(10):
            await ws.send(frame)                 # in-flight = 1
            msg = json.loads(await ws.recv())
            print(msg["seq"], msg["hand_count"], msg["infer_ms"])

asyncio.run(main())
```

值得順手驗的幾件事：`seq` 是不是連續遞增、送壞掉的位元組會不會斷線、
開滿 4 條之後第 5 條是不是被 1008 拒絕、全部斷線之後名額有沒有還回去。

---

## 這一課的誠實結論

純粹要即時追蹤的話，**[H04](H04-hands-live.md) 的瀏覽器端做法客觀上比較好**：
零頻寬、零伺服器負載、延遲更低，而且速度跟原生 Python 一樣快（16.0~16.8 ms）。

後端串流合理的時機，是伺服器要做用戶端做不到的事 ——
比對資料庫、跨使用者彙整、跑瀏覽器塞不下的大模型。
H03 目前做的事 H04 也做得到，這是刻意的對照組，對照本身就是教材。

---

## 相關

- [H02](H02-hands-upload.md)：一次一張圖的上傳版本，先看那篇比較好進入狀況
- [H04](H04-hands-live.md)：同一個模型改在瀏覽器裡跑
