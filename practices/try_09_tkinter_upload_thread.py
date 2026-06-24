"""tkinter 範例 09：上傳圖片檔案給 FastAPI（Thread 進階版）

這是 try_06_tkinter_upload.py 的進階版，後端端點、送法完全相同
（POST /api/v1/images/upload-only，用 files= 上傳），差別在把上傳丟到背景執行緒。
上傳大圖時最能體會 Thread 的好處：UI 不會在上傳期間凍結。

Thread 的觀念與範例 07 相同（詳見該檔說明）：
1. 背景執行緒負責跑 requests，避免視窗凍結。
2. tkinter 不是執行緒安全，更新畫面要用 root.after 排回主執行緒。

注意：選檔（filedialog）要留在主執行緒，因為它本身是 UI 操作；
      只有「讀檔 + 上傳」這段耗時工作才丟到背景執行緒。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""
import threading
import tkinter as tk
from tkinter import filedialog

import requests

API_URL = "http://localhost:8000/api/v1/images/upload-only"


def choose_and_upload():
    """主執行緒：先選檔（UI 操作），再把上傳交給背景執行緒。"""
    path = filedialog.askopenfilename(
        title="選擇圖片",
        filetypes=[("圖片", "*.jpg *.jpeg *.png *.webp")],
    )
    if not path:  # 使用者按取消
        return

    upload_btn.config(state="disabled")
    result_label.config(text="上傳中…")
    threading.Thread(target=worker, args=(path,), daemon=True).start()


def worker(path):
    """背景執行緒：讀檔並上傳，不碰 widget。"""
    try:
        with open(path, "rb") as f:
            files = {"file": (path, f, "image/jpeg")}
            resp = requests.post(API_URL, files=files)
        text = f"{resp.status_code}\n{resp.json()}"
    except Exception as e:
        text = f"上傳失敗：{e}"
    root.after(0, on_done, text)  # 排回主執行緒更新 UI


def on_done(text):
    """由主執行緒呼叫，安全操作 widget。"""
    result_label.config(text=text)
    upload_btn.config(state="normal")


root = tk.Tk()
root.title("上傳圖片給 FastAPI（Thread 版）")

upload_btn = tk.Button(root, text="選擇圖片並上傳", command=choose_and_upload)
upload_btn.pack(pady=12, padx=20)

# 顯示回應結果用的標籤（不指定 fg／bg，交給系統套用預設前景色，
# light/dark 主題下文字都清楚；早期寫死 fg="blue" 在深色模式會難以辨識）
result_label = tk.Label(root, text="", justify="left", wraplength=360)
result_label.pack(padx=20, pady=8)

root.mainloop()
