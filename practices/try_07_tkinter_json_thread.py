"""tkinter 範例 07：送 JSON 給 FastAPI（Thread 進階版）

這是 try_04_tkinter_json.py 的進階版，後端端點、送法完全相同
（POST /api/v1/demo/images，用 json= 送出），差別只在「怎麼送」：
把網路請求丟到背景執行緒，避免視窗凍結。

為什麼要用 Thread？
- requests 是同步的：直接在按鈕事件裡呼叫，會卡住 root.mainloop()，
  視窗在等回應期間無法重繪、無法回應點擊（看起來像當掉）。
- 改用背景執行緒跑請求，主執行緒（UI）就能保持流暢。

用 Thread 時最重要的一條規則：
- tkinter「不是」執行緒安全的：絕對不要在背景執行緒裡直接呼叫
  widget 的方法（例如 result_label.config(...)），否則行為不可預期、可能當掉。
- 正確做法：背景執行緒只負責「跑網路請求」，要更新畫面時用
  widget.after(0, 函式) 把工作「排回主執行緒」執行。after(0, ...) 的意思是
  「請主執行緒在下一輪事件迴圈儘快執行這個函式」。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""
import threading
import tkinter as tk

import requests

API_URL = "http://localhost:8000/api/v1/demo/images"


def submit():
    """按鈕事件：在主執行緒收集輸入、鎖住按鈕，再把請求交給背景執行緒。"""
    payload = {
        "title": title_entry.get(),
        "url": url_entry.get(),
        "tags": [t.strip() for t in tags_entry.get().split(",") if t.strip()],
    }

    # 送出前先把按鈕停用，避免使用者連按造成重複送出
    submit_btn.config(state="disabled")
    result_label.config(text="送出中…")

    # 建立背景執行緒執行 worker；daemon=True 讓主程式關閉時執行緒不會卡住
    threading.Thread(target=worker, args=(payload,), daemon=True).start()


def worker(payload):
    """在『背景執行緒』裡執行：只做網路請求，不碰任何 widget。"""
    try:
        resp = requests.post(API_URL, json=payload)
        text = f"{resp.status_code}\n{resp.json()}"
    except Exception as e:  # 連不到後端等錯誤，也要回報給使用者
        text = f"請求失敗：{e}"

    # 關鍵：用 after 把「更新 UI」排回主執行緒，不在這裡直接改 widget
    root.after(0, on_done, text)


def on_done(text):
    """這個函式由主執行緒透過 after 呼叫，因此可以安全地操作 widget。"""
    result_label.config(text=text)
    submit_btn.config(state="normal")  # 恢復按鈕


# ---------- 建立視窗與元件 ----------
root = tk.Tk()
root.title("送 JSON 給 FastAPI（Thread 版）")

tk.Label(root, text="標題 title").pack()
title_entry = tk.Entry(root, width=40)
title_entry.pack()

tk.Label(root, text="網址 url").pack()
url_entry = tk.Entry(root, width=40)
url_entry.pack()

tk.Label(root, text="標籤 tags（逗號分隔）").pack()
tags_entry = tk.Entry(root, width=40)
tags_entry.pack()

submit_btn = tk.Button(root, text="送出", command=submit)
submit_btn.pack(pady=8)

# 顯示回應結果用的標籤（不指定 fg／bg，交給系統套用預設前景色，
# light/dark 主題下文字都清楚；早期寫死 fg="blue" 在深色模式會難以辨識）
result_label = tk.Label(root, text="", justify="left")
result_label.pack()

root.mainloop()
