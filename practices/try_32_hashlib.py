"""教材 3.7：檔案雜湊

雜湊（hash）把任意長度的資料轉成固定長度的字串，且：
  - 同樣的輸入永遠得到同樣的輸出
  - 輸入改一個位元，輸出就完全不同
  - 無法從輸出反推回輸入

這兩個特性讓它很適合當「內容的指紋」——本課程用來做圖片去重與快取 key。

執行：uv run python practices/try_32_hashlib.py
"""

import hashlib
from pathlib import Path

print("=== 1. 字串的雜湊 ===")
data = "hello".encode("utf-8")  # hashlib 吃的是 bytes，字串要先編碼
print("md5    ", hashlib.md5(data).hexdigest())
print("sha1   ", hashlib.sha1(data).hexdigest())
print("sha256 ", hashlib.sha256(data).hexdigest())

print("\n=== 2. 改一個字元，輸出完全不同 ===")
print("hello  ", hashlib.sha256(b"hello").hexdigest())
print("hellO  ", hashlib.sha256(b"hellO").hexdigest())

print("\n=== 3. 圖檔的雜湊：分塊讀取，不把整個檔案吃進記憶體 ===")
file_path = Path("test_images/cat.jpg")
if not file_path.exists():
    print(f"找不到 {file_path}，請先放一張測試圖片")
else:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        # iter(callable, sentinel)：一直呼叫 f.read(8192) 直到回傳 b'' 為止
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)  # 可以分很多次餵進去，結果與一次餵完相同
    print(f"{file_path} → {h.hexdigest()}")

    print("\n=== 4. 用途 ===")
    print("""
  去重：上傳前先算 hash，資料庫裡已經有同樣的 hash 就不必重複存檔。
  快取 key：教材 8.5 拿它當 AI 辨識結果的 key——
            同一張圖（不管檔名是什麼）算出來的 key 一樣，就能命中快取。
""")
