"""H03：WebSocket 串流用的手部偵測 session，每條連線一個（教材 附錄 D）

跟 H02 用的 app/services/hand_landmark.py 差在哪？

H02 是「一張圖一個請求」，所以全站共用一個 detector、用一把 Lock 串起來就夠了。
H03 是「一條連線連續餵影格」，必須讓每條連線各自建一個 detector，理由有兩個：

1. 正確性：RunningMode.VIDEO 的 detector 內部有跨影格的追蹤狀態，而且
   detect_for_video() 要求時間戳嚴格遞增。兩條連線交錯呼叫同一個 detector，
   時間戳會忽前忽後，MediaPipe 直接丟 ValueError。
2. 效能：共用單例 + Lock 會把所有連線的推論串成一列，實測全站上限約 35 fps；
   每條連線各自一個 detector 的話，到 4 條都還幾乎線性擴展（每人約 49 fps）。

代價就是每條連線都吃一份資源，所以 config 那邊一定要設連線數上限。

mediapipe 是可選依賴（uv sync --extra mediapipe），和 hand_landmark.py 一樣
**只在函式內 import**：routes/hands_ws.py 會在模組頂層 import 本檔案，這裡頂層若直接
import mediapipe，核心 uv sync 的環境一啟動就整個起不來
（tests/test_smoke.py 有測試守著這件事）。
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from app.config import settings

# 解碼那段（EXIF 轉正、轉 RGB、太大就縮圖）跟 H02 完全一樣，直接沿用同一個函式
from app.services.hand_landmark import decode_image

if TYPE_CHECKING:  # 只給型別檢查器看，執行期不會 import
    from mediapipe.tasks.python.vision import HandLandmarker


class HandStreamSession:
    """一條 WebSocket 連線專用的偵測器。

    建構子會真的把模型讀進記憶體（暖機後約 8 ms，行程內第一次約 170 ms，
    要初始化 GL 與 XNNPACK），屬於阻塞的 CPU 工作，
    路由端要用 run_in_threadpool 包起來呼叫。

    建不起來時會丟兩種例外，路由各自轉成給前端看的錯誤訊息：
    - ImportError：沒裝 mediapipe
    - FileNotFoundError：模型檔不存在
    """

    def __init__(self) -> None:
        # 可選依賴，lazy import；沒裝的話 ImportError 直接往外丟給路由處理
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import (
            HandLandmarker,
            HandLandmarkerOptions,
            RunningMode,
        )

        path = settings.HAND_MODEL_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=path),
            # VIDEO 模式會沿用上一格的結果做追蹤，省掉大部分的手掌偵測，
            # 實測 27.3 ms → 16.9 ms，比逐張 IMAGE 快四成
            running_mode=RunningMode.VIDEO,
            num_hands=settings.HAND_MAX_NUM,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            # 只有 VIDEO / LIVE_STREAM 模式用得到：追蹤信心低於這個值就重新偵測
            min_tracking_confidence=0.5,
        )
        self._detector: HandLandmarker = HandLandmarker.create_from_options(options)

        # detect_for_video() 的時間戳必須嚴格遞增，記住上一次送進去的值
        self._last_ts = -1
        self.frame_count = 0

    def detect(self, content: bytes) -> dict:
        """單一影格：JPEG bytes → 關鍵點 dict。阻塞，要丟 threadpool。"""
        import mediapipe as mp  # 走到這裡 detector 已建好，代表套件一定裝了

        rgb, width, height = decode_image(content)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # 時間戳由伺服器自己用單調時鐘產生，不採用用戶端送來的值。
        # 用戶端的時鐘可能回撥、可能亂送，而只要有一格不遞增，
        # detect_for_video() 就會丟 ValueError 讓整條連線斷掉。
        # 再夾一次 max(ts, last + 1)，是防止同一毫秒內連續兩格（推論夠快時會發生）。
        ts = time.monotonic_ns() // 1_000_000
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        t0 = time.perf_counter()
        result = self._detector.detect_for_video(mp_image, ts)
        infer_ms = (time.perf_counter() - t0) * 1000

        hands = []
        for i, landmarks in enumerate(result.hand_landmarks):
            category = result.handedness[i][0]
            hands.append(
                {
                    "handedness": category.category_name,
                    "score": round(category.score, 3),
                    # 串流跟 H02 不一樣，這裡只送 x, y、而且只留四位小數：
                    # 一隻手 21 點，帶 z 又給五位小數的話每格多好幾百 bytes，
                    # 20 fps 下就是每秒多好幾 KB。畫 2D 骨架用不到 z
                    "landmarks": [{"x": round(p.x, 4), "y": round(p.y, 4)} for p in landmarks],
                }
            )

        self.frame_count += 1
        return {
            "seq": self.frame_count,
            "width": width,
            "height": height,
            "infer_ms": round(infer_ms, 1),
            "hand_count": len(hands),
            "hands": hands,
        }

    def close(self) -> None:
        """釋放模型佔用的原生資源。連線結束時一定要呼叫，
        不然每斷一次連線就漏掉一份模型記憶體與執行緒。
        """
        self._detector.close()
