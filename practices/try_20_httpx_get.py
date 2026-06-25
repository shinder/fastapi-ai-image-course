"""httpx 範例 20：基本 GET 請求（非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_10 的 requests 同步版。
對應後端：GET /api/v1/images/{id}（取得單一圖片，教材 4.6）

重點：
- httpx.AsyncClient 是非同步 HTTP 用戶端，用 async with 管理生命週期
  （離開區塊會自動關閉連線）。
- 用 await client.get(url) 送出請求；在 FastAPI 等 async 框架內呼叫外部 API 時，
  用 httpx 才不會阻塞事件迴圈（requests 是同步的，會把整個事件迴圈卡住）。
- 獨立腳本要用 asyncio.run(...) 啟動 async 函式。
- Response 的用法（status_code、headers、json()）和 requests 幾乎一樣。

執行前請先啟動後端：
    uvicorn app.main:app --reload
（並確認資料庫裡有 id=1 的圖片，可先跑 try_21_httpx_post.py 建立一筆）
"""

import asyncio

import httpx

URL = "http://localhost:8000/api/v1/images/1"


async def basic_get():
    async with httpx.AsyncClient() as client:
        r = await client.get(URL)
    print("狀態碼：", r.status_code)  # 200
    print("Content-Type：", r.headers["Content-Type"])  # application/json
    print("解析成 dict：", r.json())  # Python dict
    return r


if __name__ == "__main__":
    asyncio.run(basic_get())
