"""模擬第三方應用串接本服務（教材 綜合實作 / 5.2）

執行：
    uv run python scripts/client.py
"""

from pathlib import Path

import requests

API_BASE = "http://localhost:8000/api/v1"


def upload_and_classify(image_path: str, title: str) -> dict:
    with open(image_path, "rb") as f:
        files = {"file": (Path(image_path).name, f, "image/jpeg")}
        data = {"title": title}
        r = requests.post(
            f"{API_BASE}/images/upload-and-classify",
            files=files,
            data=data,
            timeout=60,
        )
    r.raise_for_status()
    return r.json()


def list_images(limit: int = 10) -> list:
    r = requests.get(f"{API_BASE}/images", params={"limit": limit})
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    # 1. 上傳並辨識
    result = upload_and_classify("test_images/cat.jpg", "我家的貓")
    print("辨識結果：", result["ai_result"])

    # 2. 查詢歷史
    history = list_images(limit=5)
    print(f"最近 {len(history)} 張圖片：")
    for img in history:
        print(f"  #{img['id']} {img['title']} ({img['uploaded_at']})")
