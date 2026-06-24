"""tkinter 範例 04：送 JSON 給 FastAPI

對應後端：app/routes/basic.py 的 POST /api/v1/demo/images（教材 3.2）
該端點用 Pydantic 模型 ImageCreateRequest 接收 JSON 請求主體。

重點：
- tkinter 只負責畫面與收集輸入；送 HTTP 請求是 requests 的工作。
- requests.post(url, json=...) 會把 dict 轉成 JSON，並自動帶上
  Content-Type: application/json，正好對應後端用 Pydantic 模型接收的寫法。

為什麼這個版本「不用」Thread？
- 教學上先力求簡單：先看懂「收集輸入 → 送請求 → 顯示回應」這條主線，
  不被多執行緒的複雜度干擾。
- 代價：requests 是同步的，送出當下會卡住 root.mainloop()，
  視窗在等回應的這段時間無法重繪、也無法回應點擊（看起來像「當掉」）。
  在本機、回應又快時通常感覺不明顯，但連遠端或網路慢時就很有感。
- 進階做法：把請求丟到背景執行緒，見 try_07_tkinter_json_thread.py。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""
import tkinter as tk

import requests

# 後端端點網址（FastAPI 預設跑在 8000 埠）
API_URL = "http://localhost:8000/api/v1/demo/images"


def submit():
    """按下按鈕時：收集輸入 → 組成 dict → 以 JSON 送出 → 顯示回應"""
    # 1. 從輸入框（Entry）取得使用者輸入
    payload = {
        "title": title_entry.get(),
        "url": url_entry.get(),
        # 標籤以逗號分隔，split 後轉成字串陣列（對應 schema 的 tags: list[str]）
        "tags": [t.strip() for t in tags_entry.get().split(",") if t.strip()],
    }

    # 2. 用 json= 參數送出；requests 會自動序列化並設定 Content-Type
    #    注意：requests 是同步的，送出當下視窗會短暫卡住，等回應回來才繼續。
    resp = requests.post(API_URL, json=payload)

    # 3. 把後端回應顯示在標籤上（status code + 回傳的 JSON）
    result_label.config(text=f"{resp.status_code}\n{resp.json()}")


# ---------- 建立視窗與元件 ----------
root = tk.Tk()
root.title("送 JSON 給 FastAPI")

tk.Label(root, text="標題 title").pack()
title_entry = tk.Entry(root, width=40)
title_entry.pack()

tk.Label(root, text="網址 url").pack()
url_entry = tk.Entry(root, width=40)
url_entry.pack()

tk.Label(root, text="標籤 tags（逗號分隔）").pack()
tags_entry = tk.Entry(root, width=40)
tags_entry.pack()

# command=submit：按下按鈕時呼叫 submit 函式
tk.Button(root, text="送出", command=submit).pack(pady=8)

# 顯示回應結果用的標籤（不指定 fg／bg，交給系統套用預設前景色，
# light/dark 主題下文字都清楚；早期寫死 fg="blue" 在深色模式會難以辨識）
result_label = tk.Label(root, text="", justify="left")
result_label.pack()

# 進入事件迴圈，視窗會持續顯示直到關閉
root.mainloop()
