"""requests 範例 15：Session 物件（連線重用、共用設定）

對應教材 5.3（單元五 API 串接）
對應後端：GET /users/me（教材 2.4）、GET /api/v1/images（教材 4.6）

重點：
- requests.Session() 可在多次請求間重用 TCP 連線（更快），
  並共用設定（headers、cookies…），不必每次都重帶。
- 適合「對同一個服務連續發多個請求」的情境。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import requests


def session_demo():
    session = requests.Session()
    # 設定一次，之後這個 session 發的每個請求都會自動帶上
    session.headers.update({"User-Agent": "MyApp/1.0"})

    # 兩個請求重用同一條連線、共用上面的標頭
    r1 = session.get("http://localhost:8000/users/me")  # 單元二 2.4
    r2 = session.get("http://localhost:8000/api/v1/images")  # 單元四列表
    print("users/me：", r1.json())
    print("images 筆數：", len(r2.json()))
    return r1, r2


if __name__ == "__main__":
    session_demo()
