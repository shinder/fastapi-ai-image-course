"""tkinter 範例 06：上傳圖片檔案給 FastAPI

對應後端：app/routes/images.py 的 POST /api/v1/images/upload-only（教材 3.5）
該端點用 UploadFile = File(...) 接收 multipart/form-data 的檔案。

重點：
- 用 filedialog 跳出「選檔視窗」讓使用者挑圖片。
- requests.post(url, files=...) 會以 multipart/form-data 送出，
  對應 HTML 的 <input type="file">，也對應後端的 File(...)。
- files 字典的 key（這裡是 "file"）必須和後端路由參數名一致。

為什麼這個版本「不用」Thread？
- 先力求簡單，聚焦在「files= 上傳檔案」這個重點上。
- 代價：上傳是同步的，檔案越大、網路越慢，視窗凍結越久（無法重繪/回應點擊），
  上傳大圖時這個問題會比前兩個範例更明顯。
- 進階做法：把上傳丟到背景執行緒，見 try_09_tkinter_upload_thread.py。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""
import tkinter as tk
from tkinter import filedialog

import requests

API_URL = "http://localhost:8000/api/v1/images/upload-only"


def choose_and_upload():
    """跳出選檔視窗 → 讀檔 → 以 multipart 上傳 → 顯示回應"""
    # 1. 開啟選檔對話框，只顯示常見圖片格式
    path = filedialog.askopenfilename(
        title="選擇圖片",
        filetypes=[("圖片", "*.jpg *.jpeg *.png *.webp")],
    )
    if not path:  # 使用者按取消，path 會是空字串
        return

    # 2. 以二進位模式開啟檔案，包成 requests 的 files 參數
    #    格式：{欄位名: (檔名, 檔案物件, MIME 類型)}
    with open(path, "rb") as f:
        files = {"file": (path, f, "image/jpeg")}
        resp = requests.post(API_URL, files=files)

    # 3. 顯示後端回應（會包含伺服器產生的新檔名、大小等）
    result_label.config(text=f"{resp.status_code}\n{resp.json()}")


root = tk.Tk()
root.title("上傳圖片給 FastAPI")

tk.Button(root, text="選擇圖片並上傳", command=choose_and_upload).pack(pady=12, padx=20)

# 顯示回應結果用的標籤（不指定 fg／bg，交給系統套用預設前景色，
# light/dark 主題下文字都清楚；早期寫死 fg="blue" 在深色模式會難以辨識）
result_label = tk.Label(root, text="", justify="left", wraplength=360)
result_label.pack(padx=20, pady=8)

root.mainloop()
