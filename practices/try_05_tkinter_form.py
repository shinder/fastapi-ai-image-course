"""tkinter 範例 05：送表單資料給 FastAPI

對應後端：app/routes/basic.py 的 POST /api/v1/contact（教材 3.4）
該端點用 Form(...) 接收表單欄位（不是 JSON）。

重點：
- 與範例 04 的差別只有「送法」：這裡用 data=... 而非 json=...。
- requests.post(url, data=...) 會以 application/x-www-form-urlencoded 送出，
  這正是 HTML <form> 預設的格式，對應後端的 Form(...)。
- 後端接收的型別不同（Form vs JSON），用戶端送法就要跟著換，否則會回 422。

為什麼這個版本「不用」Thread？
- 先力求簡單，聚焦在「data= 送表單」這個重點上。
- 代價：requests 同步執行，送出當下視窗會短暫凍結（無法重繪/回應點擊）。
- 進階做法：把請求丟到背景執行緒，見 try_08_tkinter_form_thread.py。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""
import tkinter as tk

import requests

API_URL = "http://localhost:8000/api/v1/contact"


def submit():
    """收集輸入 → 以表單格式送出 → 顯示回應"""
    # 表單欄位名稱（name/email/message）必須和後端 Form 參數名一致
    payload = {
        "name": name_entry.get(),
        "email": email_entry.get(),
        "message": msg_entry.get(),
    }

    # 關鍵：用 data=（而非 json=），送出 x-www-form-urlencoded 格式
    resp = requests.post(API_URL, data=payload)

    result_label.config(text=f"{resp.status_code}\n{resp.json()}")


root = tk.Tk()
root.title("送表單給 FastAPI")

tk.Label(root, text="姓名 name").pack()
name_entry = tk.Entry(root, width=40)
name_entry.pack()

tk.Label(root, text="Email").pack()
email_entry = tk.Entry(root, width=40)
email_entry.pack()

tk.Label(root, text="訊息 message").pack()
msg_entry = tk.Entry(root, width=40)
msg_entry.pack()

tk.Button(root, text="送出", command=submit).pack(pady=8)

result_label = tk.Label(root, text="", fg="blue", justify="left")
result_label.pack()

root.mainloop()
