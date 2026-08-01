"""下載 MediaPipe 模型檔

MediaPipe 的推論模型（.task）不隨 pip 套件附帶，必須另外下載。
模型檔體積不小（手部模型約 7.5 MB），所以不進版控，改用這支腳本取得。

用法（在專案根目錄執行）：
    uv run python scripts/download_models.py

已經下載過的檔案會直接略過；要強制重新下載就先把 ml_models/ 刪掉。
"""

import os
import sys

import requests

# 模型存放目錄（相對於專案根目錄，與 app/config.py 的 HAND_MODEL_PATH 預設值一致）
MODEL_DIR = "./ml_models"

# 要下載的模型清單：檔名 → 下載網址
MODELS = {
    # 手部關鍵點：每隻手 21 個點。float16 版體積小、CPU 上夠快
    "hand_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models"
        "/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    ),
}


def download(name: str, url: str) -> None:
    """下載單一模型檔，已存在就略過"""
    dest = os.path.join(MODEL_DIR, name)

    if os.path.exists(dest):
        size = os.path.getsize(dest)
        print(f"[略過] {dest} 已存在（{size:,} bytes）")
        return

    print(f"[下載] {name}\n        來源：{url}")

    # stream=True 邊下載邊寫檔，避免整個檔案先塞進記憶體
    with requests.get(url, stream=True, timeout=60) as res:
        res.raise_for_status()

        # 先寫到 .part 暫存檔，下載完成才改名，
        # 這樣中途按 Ctrl+C 不會留下一個看似完整、其實壞掉的模型檔
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            for chunk in res.iter_content(chunk_size=1024 * 256):
                f.write(chunk)
        os.replace(tmp, dest)

    print(f"[完成] {dest}（{os.path.getsize(dest):,} bytes）")


def main() -> int:
    os.makedirs(MODEL_DIR, exist_ok=True)

    for name, url in MODELS.items():
        try:
            download(name, url)
        except requests.RequestException as exc:
            print(f"[失敗] {name}：{exc}", file=sys.stderr)
            return 1

    print("\n模型準備完成，可以啟動應用了：uv run uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
