"""下載並驗證 MediaPipe 模型檔

MediaPipe 的推論模型（.task）不隨 pip 套件附帶，必須另外下載。
模型檔體積不小（手部模型約 7.5 MB），所以不進版控，改用這支腳本取得。

用法（在專案根目錄執行）：
    uv run python scripts/download_models.py           # 下載缺少的、驗證已存在的
    uv run python scripts/download_models.py --check   # 只驗證不下載（開課前檢查用）
    uv run python scripts/download_models.py --force   # 強制重新下載

為什麼要驗證 SHA-256：教室網路常有 proxy 或流量限制，下載可能中途被截斷，
或者拿回一頁 HTML 錯誤頁而不是模型檔。這種檔案「看起來存在」，
但要等到載入模型時才會爆出難以理解的錯誤——那時通常已經沒有時間排查了。
事前比對雜湊就能當場發現，這也是教材 3.7 講的雜湊用途之一。
"""

import argparse
import hashlib
import os
import sys
import time

import requests

# 模型存放目錄（相對於專案根目錄，與 app/config.py 的 HAND_MODEL_PATH 預設值一致）
MODEL_DIR = "./ml_models"

# 要下載的模型：檔名 → (下載網址, 位元組數, sha256)
MODELS = {
    # 手部關鍵點：每隻手 21 個點。float16 版體積小、CPU 上夠快
    "hand_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models"
        "/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
        7819105,
        "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
    ),
}

RETRIES = 3


def sha256_of(path: str) -> str:
    """分塊算檔案的 SHA-256（教材 3.7），大檔也不會吃滿記憶體"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path: str, size: int, digest: str) -> tuple[bool, str]:
    """檢查檔案是否完整，回傳 (是否通過, 說明)"""
    if not os.path.exists(path):
        return False, "檔案不存在"
    actual_size = os.path.getsize(path)
    if actual_size != size:
        return False, f"大小不符（預期 {size:,}、實際 {actual_size:,}）"
    actual = sha256_of(path)
    if actual != digest:
        return False, f"雜湊不符（預期 {digest[:16]}…、實際 {actual[:16]}…）"
    return True, "完整"


def download(name: str, url: str, size: int, digest: str, force: bool) -> bool:
    """下載單一模型檔並驗證；已存在且驗證通過就略過"""
    dest = os.path.join(MODEL_DIR, name)

    if os.path.exists(dest) and not force:
        ok, why = verify(dest, size, digest)
        if ok:
            print(f"[OK] {dest}（{size:,} bytes，雜湊相符）")
            return True
        # 存在但壞掉——正是「看起來有檔案卻用不了」的情況，直接重抓
        print(f"[重抓] {dest} {why}")

    for attempt in range(1, RETRIES + 1):
        print(f"[下載] {name}（第 {attempt}/{RETRIES} 次）")
        # 先寫到 .part 暫存檔，驗證通過才改名，
        # 這樣中途中斷不會留下一個看似完整、其實壞掉的模型檔
        tmp = dest + ".part"
        try:
            # stream=True 邊下載邊寫檔，避免整個檔案先塞進記憶體
            with requests.get(url, stream=True, timeout=60) as res:
                res.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 256):
                        f.write(chunk)

            ok, why = verify(tmp, size, digest)
            if not ok:
                os.remove(tmp)
                print(f"[失敗] 下載內容不正確：{why}", file=sys.stderr)
                if attempt < RETRIES:
                    time.sleep(2 * attempt)
                    continue
                return False

            os.replace(tmp, dest)  # 原子性改名，到這一步才算數
            print(f"[完成] {dest}（{size:,} bytes）")
            return True

        except requests.RequestException as exc:
            if os.path.exists(tmp):
                os.remove(tmp)
            print(f"[失敗] {exc}", file=sys.stderr)
            if attempt < RETRIES:
                time.sleep(2 * attempt)

    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="下載並驗證 MediaPipe 模型檔")
    parser.add_argument("--check", action="store_true", help="只驗證現有檔案，不下載")
    parser.add_argument("--force", action="store_true", help="強制重新下載")
    args = parser.parse_args()

    os.makedirs(MODEL_DIR, exist_ok=True)
    failed = []

    for name, (url, size, digest) in MODELS.items():
        dest = os.path.join(MODEL_DIR, name)
        if args.check:
            ok, why = verify(dest, size, digest)
            print(f"[{'OK' if ok else '不合格'}] {dest}：{why}")
            if not ok:
                failed.append(name)
            continue
        if not download(name, url, size, digest, args.force):
            failed.append(name)

    if failed:
        print(f"\n以下模型未就緒：{', '.join(failed)}", file=sys.stderr)
        print("可用瀏覽器手動下載存到 ml_models/，再跑一次 --check 確認：", file=sys.stderr)
        for name in failed:
            print(f"  {MODELS[name][0]}", file=sys.stderr)
        return 1

    print(
        "\n全部模型驗證通過。"
        if args.check
        else "\n模型準備完成：uv run uvicorn app.main:app --reload"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
