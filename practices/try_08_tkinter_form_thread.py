"""tkinter 範例 08：送表單資料給 FastAPI（Thread 進階版）

這是 try_05_tkinter_form.py 的進階版，後端端點、送法完全相同
（POST /api/v1/contact，用 data= 送表單），差別只在把請求丟到背景執行緒。

Thread 的觀念與範例 07 相同（詳見該檔說明），這裡只重述兩個重點：
1. 背景執行緒負責跑 requests，避免視窗凍結。
2. tkinter 不是執行緒安全，更新畫面要用 root.after 排回主執行緒。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""
import threading
import tkinter as tk

import requests

API_URL = "http://localhost:8000/api/v1/contact"


def submit():
    """主執行緒：收集輸入、鎖按鈕，再把請求交給背景執行緒。"""
    payload = {
        "name": name_entry.get(),
        "email": email_entry.get(),
        "message": msg_entry.get(),
    }
    submit_btn.config(state="disabled")
    result_label.config(text="送出中…")
    threading.Thread(target=worker, args=(payload,), daemon=True).start()


def worker(payload):
    """背景執行緒：只做網路請求，不碰 widget。"""
    try:
        resp = requests.post(API_URL, data=payload)  # data= 送表單格式
        text = f"{resp.status_code}\n{resp.json()}"
    except Exception as e:
        text = f"請求失敗：{e}"
    root.after(0, on_done, text)  # 排回主執行緒更新 UI


def on_done(text):
    """由主執行緒呼叫，安全操作 widget。"""
    result_label.config(text=text)
    submit_btn.config(state="normal")


root = tk.Tk()
root.title("送表單給 FastAPI（Thread 版）")

tk.Label(root, text="姓名 name").pack()
name_entry = tk.Entry(root, width=40)
name_entry.pack()

tk.Label(root, text="Email").pack()
email_entry = tk.Entry(root, width=40)
email_entry.pack()

tk.Label(root, text="訊息 message").pack()
msg_entry = tk.Entry(root, width=40)
msg_entry.pack()

submit_btn = tk.Button(root, text="送出", command=submit)
submit_btn.pack(pady=8)

# 顯示回應結果用的標籤（不指定 fg／bg，交給系統套用預設前景色，
# light/dark 主題下文字都清楚；早期寫死 fg="blue" 在深色模式會難以辨識）
result_label = tk.Label(root, text="", justify="left")
result_label.pack()

root.mainloop()
