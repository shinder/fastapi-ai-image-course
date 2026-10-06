# H04：瀏覽器端即時推論

> 教材 附錄 D「MediaPipe 進階：串流與瀏覽器端推論」的實作說明，三篇之三。
> 後端的基礎（Tasks API、單例、優雅降級）在教材 8.7。

對應頁面 `app/static/demos/H04-hands-live.html`
（啟動後開 <http://localhost:8000/static/demos/H04-hands-live.html>）。**沒有對應的 API 端點** —— 這正是重點。

一句話：**同一個模型檔下載到瀏覽器，用 WebAssembly + WebGL 在本機跑，
影像完全不離開這台電腦，伺服器只負責供應 HTML 與模型檔。**

前兩頁（[H02](H02-hands-upload.md)、[H03](H03-hands-ws.md)）都是把影像送到後端算。
這一頁把同一件事搬回瀏覽器，用來回答一個一定會冒出來的問題：
**那到底該放哪邊算？**

---

## 涉及的檔案

| 檔案 | 負責什麼 |
|---|---|
| `app/static/demos/H04-hands-live.html` | 全部的事 |
| `app/main.py` | 把 `ml_models/` 掛成 `/models`，讓瀏覽器抓得到模型檔 |
| `ml_models/hand_landmarker.task` | 模型檔（約 7.5 MB，已隨版控附上） |
| `scripts/download_models.py` | 模型檔遺失時用來重新下載 |

後端的 Python 部分（`app/services/`、`app/routes/hands*.py`）**完全沒有參與** ——
連後端沒裝 `mediapipe`（沒跑 `uv sync --extra mediapipe`）這一頁也照樣能用。

---

## 整體流程

```
瀏覽器                                                  FastAPI
  |                                                        |
  |  (a) GET /static/demos/H04-hands-live.html             |
  |------------------------------------------------------->|
  |  (b) GET .../tasks-vision@0.10.35/vision_bundle.mjs     |   （CDN）
  |  (c) GET .../tasks-vision@0.10.35/wasm/*                |   （CDN，約 11 MB）
  |  (d) GET /models/hand_landmarker.task                   |
  |------------------------------------------------------->|  約 7.5 MB
  |<-------------------------------------------------------|
  |  (e) 預熱：對一張空白圖跑一次推論（約 4.7 秒）           |
  |                                                        |
  |  ===== 以下完全沒有網路流量 =====                       |
  |                                                        |
  |  (f) getUserMedia → <video>                            |
  |  (g) requestAnimationFrame 迴圈：                       |
  |        鏡射畫進 canvas                                  |
  |        detectForVideo(canvas, now)   ← 約 16 ms         |
  |        用 DrawingUtils 畫骨架                           |
  |      （無限循環，一格網路封包都不會送出）                 |
```

從 (f) 開始，把網路線拔掉這一頁照樣運作。

---

## 模型從哪裡來

```js
import {
    FilesetResolver,
    HandLandmarker,
    DrawingUtils,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/vision_bundle.mjs";
```

這一頁沒有 npm、沒有打包工具，就是瀏覽器原生的 ES module import。
所以 `<script>` 必須寫成 `<script type="module">`。

版本固定寫在網址裡（`@0.10.35`），不會自己升級。這是 JavaScript 套件，
跟後端 Python 的 `mediapipe`（版本由 `uv.lock` 決定）是各自獨立的兩份實作，版本不必相同也能跑；
兩邊共用的只有同一個 `.task` 模型檔。不過要做嚴謹的對照實驗時最好把兩邊的版本對齊 ——
版本不同的話，同一張圖在兩邊算出來的座標可能有微小差異。

```js
const fileset = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm"
);
handLandmarker = await HandLandmarker.createFromOptions(fileset, {
    baseOptions: {
        modelAssetPath: "/models/hand_landmarker.task",   // 自己的伺服器
        delegate: "GPU",
    },
    runningMode: "VIDEO",
    numHands: 2,
    minHandDetectionConfidence: 0.5,
    minHandPresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
});
```

WASM 檔（約 11 MB）從 CDN 抓，**模型檔（7.5 MB）從自己的伺服器抓**：

```python
# app/main.py
os.makedirs(os.path.dirname(settings.HAND_MODEL_PATH) or ".", exist_ok=True)
app.mount(
    "/models",
    StaticFiles(directory=os.path.dirname(settings.HAND_MODEL_PATH) or "."),
    name="models",
)
```

模型從自己的伺服器供應（而不是連 Google 的網址），教室網路不通時也能上課，
而且用的是跟後端 Python 完全同一個檔案 —— 對照實驗才有意義。

`delegate: "GPU"` 走 WebGL。改成 `"CPU"` 也能跑，但慢很多，可以自己改改看、比較 badge 上的數字。

---

## 預熱：這一頁最容易被忽略的一段

```js
my_status.textContent = '正在初始化 GPU（第一次會久一點）...';
const warmup = document.createElement('canvas');
warmup.width = 640;
warmup.height = 480;
warmup.getContext('2d').fillRect(0, 0, 640, 480);
handLandmarker.detectForVideo(warmup, performance.now());
```

**第一次推論要編譯 GPU shader，實測會卡將近 5 秒。**

不先做掉的話，使用者一按下「開啟攝影機」整頁就凍住 ——
而且因為是同步的 WASM 呼叫，連載入動畫都不會轉。使用者會以為沒反應而狂點按鈕，
那些點擊會在解凍後一次補送出來，把剛開好的攝影機又關掉。

所以在按鈕按下**之前**就先用一張空白畫布跑一次，把這個一次性成本挪到載入階段，
按鈕在這之前都是 disabled 的：

```html
<button type="button" class="btn btn-primary" id="my_start_btn" disabled>載入模型中...</button>
```

這種「一次性初始化成本」在後端是使用者感覺不到的（H02 在 lifespan 啟動時就載好了，
H03 則是在送出 `ready` 之前建好），在瀏覽器端卻會直接卡住畫面。

---

## 主迴圈

```js
function loop() {
    if (!running) return;

    // 1. 鏡射畫進 canvas
    ctx.save();
    ctx.scale(-1, 1);
    ctx.translate(-my_canvas.width, 0);
    ctx.drawImage(my_video, 0, 0, my_canvas.width, my_canvas.height);
    ctx.restore();

    // 2. 影片時間有前進才重跑推論
    if (my_video.currentTime !== lastVideoTime) {
        lastVideoTime = my_video.currentTime;
        lastResult = handLandmarker.detectForVideo(my_canvas, performance.now());
    }

    // 3. 畫骨架
    if (lastResult) { ... }

    requestAnimationFrame(loop);
}
```

### 為什麼要檢查 `currentTime`

螢幕是 120 Hz、攝影機只有 30 fps 時，`requestAnimationFrame` 一秒會跑 120 次，
但其中只有 30 次拿得到新畫面。不檢查的話有四分之三的推論是在算同一張圖。
這一行省掉一半以上的計算量。

H03 沒有這個問題，因為那邊的節奏是由網路來回決定的。

### 餵給模型的是 canvas 不是 video

```js
lastResult = handLandmarker.detectForVideo(my_canvas, performance.now());
```

注意第一個參數是**已經鏡射過的 canvas**，不是原始的 `<video>`。
理由跟 H03 完全一樣：MediaPipe 判定 Left／Right 時假設輸入影像已經鏡射過。
直接餵 `my_video`，畫面看起來對，但左右手標籤會全部相反。

`detectForVideo` 是**同步**的，直接回傳結果，不像後端要 await ——
這也是為什麼預熱那 5 秒會整頁凍住。

---

## 畫骨架：這裡可以偷懶

H02／H03 都得自己維護一份 21 點的連線表：

```js
const HAND_CONNECTIONS = [
    [0, 1], [1, 2], [2, 3], [3, 4],    // 拇指
    ...
];
```

H04 不用，因為 `tasks-vision` 內建了：

```js
const drawingUtils = new DrawingUtils(ctx);

drawingUtils.drawConnectors(landmarks, HandLandmarker.HAND_CONNECTIONS, {
    color: color,
    lineWidth: 4,
});
drawingUtils.drawLandmarks(landmarks, {
    color: '#ff1744',
    radius: 4,
});
```

`HandLandmarker.HAND_CONNECTIONS` 就是那張連線表的官方版本。
前兩頁的手寫版本是為了看清楚 21 個點怎麼連起來 —— 兩種都值得看過一次。

### 結果物件的欄位名

```js
lastResult.landmarks          // 陣列，每隻手一組 21 點
lastResult.handednesses[i][0] // 注意是複數 handednesses
```

JS 版用 `handednesses`（舊版叫 `handedness`，已標記為過時），
Python 版則是 `result.hand_landmarks` 與 `result.handedness`。
**兩邊的欄位名不一樣**，對照著看的時候很容易搞混。

座標一樣是 0~1 的正規化值，乘上 canvas 尺寸就是像素位置 —— 這點三頁完全一致。

---

## 跟前兩頁的對照

| | H02 | H03 | H04 |
|---|---|---|---|
| 推論在哪 | 後端 Python | 後端 Python | 瀏覽器 WASM |
| 傳輸 | 一次一張圖 | WebSocket 連續 | 不傳 |
| 執行模式 | `IMAGE` | `VIDEO` | `VIDEO` |
| 推論時間 | 27.3 ms | 16.9 ms | 16.0~16.8 ms |
| 端到端延遲 | 一次請求 | 約 18~19 ms | 約等於推論時間 |
| 頻寬 | 每張圖一次 | 約 240 KB/s | 只有初次載入 |
| 伺服器負載 | 每請求一次推論 | 每連線一個 detector | 零 |
| 影像外流 | 會（而且存檔） | 會 | 不會 |
| 初次成本 | 無 | 無 | 約 19 MB 下載 + 5 秒暖機 |
| 多人使用 | 排隊 | 上限 4 條 | 無上限（各自的電腦） |

表中的時間是在 M3 Mac 上、以 640x480 影像與 `mediapipe` 0.10.35 實測的數字。
換一台機器或換個版本都會有出入，值得在自己的電腦上量一次。

### 兩個反直覺的結論

**一、瀏覽器不比後端慢。** WASM + WebGL 是 16.0~16.8 ms，
原生 Python 的 VIDEO 模式是 16.9 ms —— 實質上一樣快。
「重的計算就該丟後端」這個直覺在這個案例是錯的。

**二、降解析度不會加速推論。** 640x480 是 16.9 ms，320x240 是 17.3 ms，沒有變快。
模型內部本來就會把圖縮到 192／224 像素，降解析度**只省頻寬**。
所以 H03 把影格壓到 480x360 是為了省網路，不是為了讓伺服器算得快。

### 那到底該放哪邊算

純粹要即時追蹤 —— **H04 客觀上是最好的**：零頻寬、零伺服器負載、延遲最低、
人數無上限、影像不外流，而且速度一樣。

後端算合理的時機是**伺服器要做用戶端做不到的事**：

- 需要比對資料庫（例如認出這是誰的手勢、跟歷史紀錄比較）
- 需要跨使用者彙整（多人同時比手勢的互動裝置）
- 模型大到瀏覽器塞不下，或權重不能外流
- 需要留存證據（H02 那種存檔 + 寫資料庫的情境）

H03 目前做的事 H04 也做得到，那是刻意的對照組。
把三頁的數字擺在一起自己判斷，比直接背結論有用。

---

## 隱私這件事值得講

H04 的 `<video>` 是 hidden 的，畫面只出現在 canvas 上，而且**沒有任何一個位元組送出去**。
H02 不只送出去，還存進 `uploads/` 並寫進資料庫。

同一個功能、同一個模型，三種架構的隱私性質完全不同。
這在做人臉、手勢、居家攝影機這類應用時是實打實的設計決定，不是加分項。

---

## 常見問題

**Q：載入卡在「正在下載 WebAssembly 與模型」。**
CDN 連不上（教室網路擋外部 CDN 是常見狀況）。模型檔是從自己的伺服器抓的沒問題，
但 WASM 還是走 CDN。要完全離線的話，得把 `@mediapipe/tasks-vision` 的
`wasm/` 目錄也放到自己的靜態目錄下，並改掉 `FilesetResolver.forVisionTasks()` 的路徑。

**Q：模型檔 404。**
先確認 `ml_models/hand_landmarker.task` 還在；不見了就跑 `uv run python scripts/download_models.py` 重新下載。
`/models` 是掛在 `HAND_MODEL_PATH` 的所在目錄（預設 `./ml_models/`）。

**Q：第一次按開啟攝影機整頁凍住。**
預熱那段沒跑到，或是在預熱完成前就按了按鈕。確認按鈕的 `disabled`
是在預熱之後才解除的。

**Q：左右手標籤反了。**
確認 `detectForVideo` 餵的是鏡射過的 canvas，不是原始的 `<video>`。

**Q：fps 顯示 0 或很怪。**
分頁切到背景時 `requestAnimationFrame` 會停住（瀏覽器正常的省電行為），
切回來時中間有個好幾秒的大洞。程式裡對超過一秒的間隔會把舊資料丟掉重算。

**Q：攝影機開不起來。**
`getUserMedia` 只在安全環境（HTTPS 或 localhost）可用。
用區網 IP 開這一頁會失敗，要用 cloudflared 開 HTTPS 通道（教材 4.5）。

---

## 相關

- [H02](H02-hands-upload.md)：一次一張圖上傳給後端，會存檔與寫資料庫
- [H03](H03-hands-ws.md)：WebSocket 串流給後端，重點在回壓控制
