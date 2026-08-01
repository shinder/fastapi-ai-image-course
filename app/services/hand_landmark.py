"""MediaPipe 手部關鍵點偵測（Tasks API）

一隻手會被標示出 21 個關鍵點（手腕、每根手指的四個關節），
每個點都是 0~1 的正規化座標，乘上圖片寬高就是實際像素位置。

重要：新版 mediapipe 已經把舊的 mp.solutions.* 整個移除，只剩 mediapipe.tasks。
網路上常見的 mp.solutions.hands.Hands() 寫法在 0.10.35 會直接 AttributeError，
請一律用本檔案示範的 Tasks API。

為什麼要獨立成 services 層：
推論邏輯跟 HTTP 無關，抽出來之後路由檔可以維持輕薄，
之後要改接 WebSocket 即時串流或換別的模型，也不必動到路由。
"""

import os
import threading
from io import BytesIO

import numpy as np
from PIL import Image as PILImage, ImageOps

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

from app.config import settings

# 模組層單例：建立 detector 要花一秒左右（要把模型讀進記憶體、初始化 GPU），
# 不可能每個請求建一次，所以啟動時建好一直重複用。
# 這跟 app/database.py 的 engine 是同一種模式：模組只會被 import 一次。
_detector: HandLandmarker | None = None

# MediaPipe 從未保證 detector 可以被多執行緒同時呼叫，而 FastAPI 會把
# run_in_threadpool 的工作丟到不同執行緒，所以用鎖把 detect() 串成一次一個。
# 補充：0.10.31 之後 MediaPipe 內部已經用單一執行緒把所有 C 呼叫序列化，
# 所以這把鎖不會讓速度變慢（本來就沒有平行度），但語意明確、也不依賴實作細節。
_lock = threading.Lock()


def load_detector() -> bool:
    """應用啟動時（lifespan）呼叫，預先把模型載入記憶體。

    採用與 database.init_db() 相同的優雅降級策略：
    模型檔不存在時不讓整個應用崩潰，只印出清楚的警告與下載指令並回傳 False，
    這樣其他不需要 AI 的路由仍可正常使用，手部相關端點則會回 503。
    """
    global _detector

    if _detector is not None:
        return True

    path = settings.HAND_MODEL_PATH
    if not os.path.exists(path):
        print("=" * 70)
        print("找不到 MediaPipe 手部模型檔，手部偵測端點將無法使用。")
        print(f"   預期路徑：{path}")
        print("   → 請執行：uv run python scripts/download_models.py")
        print("=" * 70)
        return False

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=path),
        # IMAGE：單張獨立圖片。另有 VIDEO / LIVE_STREAM 供影片逐格追蹤使用
        running_mode=RunningMode.IMAGE,
        num_hands=settings.HAND_MAX_NUM,
        # 門檻調高會比較不容易誤判，但也比較容易漏掉手
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
    )
    _detector = HandLandmarker.create_from_options(options)

    print(f"MediaPipe 手部模型載入完成：{path}")
    return True


def close_detector() -> None:
    """應用關閉時（lifespan）呼叫，釋放模型佔用的原生資源"""
    global _detector

    if _detector is not None:
        _detector.close()
        _detector = None


def is_ready() -> bool:
    """模型是否已備妥，路由用它決定要不要回 503"""
    return _detector is not None


def decode_image(content: bytes) -> tuple[np.ndarray, int, int]:
    """圖檔 bytes → (RGB uint8 的 numpy 陣列, 原圖寬, 原圖高)

    四個處理都是必要的，少一個就會遇到奇怪的問題：
    - exif_transpose：手機拍的照片常常是「橫著存、靠 EXIF 標記轉正」，
      不處理的話餵給模型的是躺著的圖，偵測率會很差；
      瀏覽器顯示時會自動套用這個標記，所以後端也要做，兩邊座標才對得上
    - convert("RGB")：統一處理灰階(L)、含透明度(RGBA)、調色盤(P) 等模式，
      確保拿到的是三通道，mp.Image 的 SRGB 格式只吃三通道
    - thumbnail：8000x6000 的大圖推論會很慢。因為回傳的是 0~1 的正規化座標，
      縮圖完全不影響座標意義，前端仍然用自己的顯示尺寸去乘
    - ascontiguousarray：mp.Image 會把陣列的記憶體位址直接交給 C 函式，
      要求記憶體連續的 uint8
    """
    img = PILImage.open(BytesIO(content))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    # 轉正之後才是使用者實際看到的尺寸
    source_width, source_height = img.size

    max_side = settings.HAND_MAX_SIDE
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side))

    rgb = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))
    return rgb, source_width, source_height


def detect(content: bytes) -> dict:
    """對單張圖片做手部關鍵點偵測，回傳可直接 JSON 序列化的 dict。

    這是一個「阻塞的 CPU 工作」，路由端必須用 run_in_threadpool 包起來呼叫，
    不然會卡住整個 event loop，其他請求全部要排隊。

    沒偵測到手不算錯誤，會回 hand_count = 0、hands = []。
    """
    if _detector is None:
        raise RuntimeError("手部模型尚未載入")

    rgb, width, height = decode_image(content)
    processed_height, processed_width = rgb.shape[:2]
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    with _lock:  # detector 非 thread-safe，同一時間只讓一個請求進來推論
        result = _detector.detect(mp_image)

    hands = []
    for i, landmarks in enumerate(result.hand_landmarks):
        # handedness[i] 是一串分類結果，第 0 個就是分數最高的那個
        category = result.handedness[i][0]
        hands.append(
            {
                "index": i,
                # 注意：MediaPipe 的 Left / Right 是以「鏡像後的影像」為基準判定，
                # 自拍鏡頭沒有取消鏡像的話，看起來會跟直覺相反
                "handedness": category.category_name,
                "score": round(category.score, 4),
                # x, y 是相對於圖片寬高的 0~1 正規化座標；
                # z 是相對於手腕的深度（越小代表離鏡頭越近），單位與 x 大致同尺度
                "landmarks": [
                    {"x": round(p.x, 5), "y": round(p.y, 5), "z": round(p.z, 5)} for p in landmarks
                ],
            }
        )

    return {
        # 原圖尺寸（已套用 EXIF 轉正），前端拿它換算像素座標
        "width": width,
        "height": height,
        # 實際送進推論的尺寸，太大的圖會先被縮小；
        # 因為座標是正規化的，這個差異不影響前端怎麼畫
        "processed_width": processed_width,
        "processed_height": processed_height,
        "model": "hand_landmarker",
        "mediapipe_version": mp.__version__,
        "hand_count": len(hands),
        "hands": hands,
    }
