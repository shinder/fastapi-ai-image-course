"""附錄 D：MediaPipe 手部關鍵點偵測

和 Ollama 視覺模型（教材 8.4）是互補的兩種工具：
  - MediaPipe：幾 MB 的專用模型，數十毫秒就回傳「手在哪裡」的結構化座標
  - 視覺模型：幾 GB 的通用模型，數秒回傳「這是什麼、代表什麼」的自然語言

需要的東西：
    uv sync --extra mediapipe
    curl -o ml_models/hand_landmarker.task \\
      https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

執行：
    uv run python -m practices.try_40_mediapipe_hand [圖片路徑]
"""

import sys
from pathlib import Path

MODEL_PATH = Path("ml_models/hand_landmarker.task")

# 21 個關鍵點裡比較好認的幾個（編號是固定的）
NAMED_POINTS = {
    0: "手腕",
    4: "拇指指尖",
    8: "食指指尖",
    12: "中指指尖",
    16: "無名指指尖",
    20: "小指指尖",
}


def build_detector(num_hands: int = 2):
    """建立偵測器。載入一次重複使用——同教材 8.4 的 Client 重用原則。"""
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
        num_hands=num_hands,
        min_hand_detection_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def detect(image_path: str) -> list[dict]:
    """回傳每隻手的關鍵點座標（x / y 是 0~1 的相對座標，與圖片尺寸無關）。"""
    import mediapipe as mp

    detector = build_detector()
    image = mp.Image.create_from_file(image_path)
    result = detector.detect(image)

    hands = []
    for i, landmarks in enumerate(result.hand_landmarks):
        # handedness 是左右手判定，信心度最高的那個放在 [0]
        side = result.handedness[i][0].category_name if i < len(result.handedness) else "?"
        hands.append(
            {
                "side": side,
                "points": [
                    {
                        "index": k,
                        "name": NAMED_POINTS.get(k),
                        "x": round(p.x, 4),
                        "y": round(p.y, 4),
                    }
                    for k, p in enumerate(landmarks)
                ],
            }
        )
    return hands


def count_extended_fingers(points: list[dict]) -> int:
    """粗略判斷伸出幾根手指：指尖比第二指節高（y 較小）就算伸直。

    只是示範「有了座標就能自己定規則」——不需要再訓練任何模型。
    注意這個判斷假設手是正立的，手轉了角度就不準。
    """
    tips_and_pips = [(8, 6), (12, 10), (16, 14), (20, 18)]  # 食指到小指
    extended = sum(1 for tip, pip in tips_and_pips if points[tip]["y"] < points[pip]["y"])
    # 拇指改比 x（它是橫向張開的）
    if abs(points[4]["x"] - points[17]["x"]) > abs(points[3]["x"] - points[17]["x"]):
        extended += 1
    return extended


def main() -> None:
    image_path = sys.argv[1] if len(sys.argv) > 1 else "test_images/hand.jpg"

    if not MODEL_PATH.exists():
        print(f"找不到模型檔 {MODEL_PATH}")
        print("請先下載（見本檔開頭的說明）")
        return
    if not Path(image_path).exists():
        print(f"找不到圖片 {image_path}")
        print("用法：uv run python -m practices.try_40_mediapipe_hand <圖片路徑>")
        return

    try:
        hands = detect(image_path)
    except ImportError:
        print("尚未安裝 mediapipe，請先執行：uv sync --extra mediapipe")
        return

    if not hands:
        print("這張圖裡沒有偵測到手")
        return

    print(f"偵測到 {len(hands)} 隻手\n")
    for i, hand in enumerate(hands, 1):
        print(
            f"第 {i} 隻手（{hand['side']}）：伸出約 {count_extended_fingers(hand['points'])} 根手指"
        )
        for p in hand["points"]:
            if p["name"]:
                print(f"    {p['name']:<10} ({p['x']}, {p['y']})")
        print()


if __name__ == "__main__":
    main()
