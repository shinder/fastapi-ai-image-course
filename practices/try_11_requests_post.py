"""requests 範例 11：基本 POST 請求（送 JSON）

對應教材 5.2（單元五 API 串接）
對應後端：POST /api/v1/images（建立圖片，教材 4.6）

重點：
- requests.post(url, json=data) 會把 dict 序列化成 JSON，
  並自動帶上 Content-Type: application/json。
- 對應後端用 Pydantic 模型 ImageCreate 接收（欄位 title / description）。
- 建立成功回 201，回應主體是新建立的資源（含自動產生的 id）。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import requests

URL = "http://localhost:8000/api/v1/images"


def basic_post():
    # 欄位對齊後端 ImageCreate：title（必填）、description（選填）
    data = {"title": "我的圖片", "description": "一張示範圖片"}
    r = requests.post(URL, json=data)
    print("狀態碼：", r.status_code)  # 201
    print("回應：", r.json())  # 新建立的圖片（含 id）
    return r


if __name__ == "__main__":
    basic_post()
