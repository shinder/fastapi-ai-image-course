"""httpx 範例 21：基本 POST 請求（送 JSON，非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_11 的 requests 同步版。
對應後端：POST /api/v1/images（建立圖片，教材 4.6）

重點：
- await client.post(url, json=data)：和 requests 一樣用 json= 送出，
  httpx 會自動序列化成 JSON 並帶上 Content-Type: application/json。
- 對應後端用 Pydantic 模型 ImageCreate 接收（欄位 title / description）。
- 建立成功回 201，回應主體是新建立的資源（含自動產生的 id）。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import asyncio

import httpx

URL = "http://localhost:8000/api/v1/images"


async def basic_post():
    # 欄位對齊後端 ImageCreate：title（必填）、description（選填）
    data = {"title": "我的圖片", "description": "一張示範圖片"}
    async with httpx.AsyncClient() as client:
        r = await client.post(URL, json=data)
    print("狀態碼：", r.status_code)  # 201
    print("回應：", r.json())  # 新建立的圖片（含 id）
    return r


if __name__ == "__main__":
    asyncio.run(basic_post())
