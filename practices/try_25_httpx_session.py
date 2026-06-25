"""httpx 範例 25：AsyncClient 重用（連線重用、共用設定，非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_15 的 requests Session 版。
對應後端：GET /users/me（教材 2.4）、GET /api/v1/images（教材 4.6）

重點：
- httpx 沒有「Session」這個名字——AsyncClient 本身就扮演 requests.Session 的角色：
  重用 TCP 連線、共用 headers / cookies。
- 額外好處：可設 base_url，之後請求只要寫相對路徑（/users/me）即可。
- 所以「用同一個 AsyncClient 連發多個請求」就是 httpx 的連線重用慣例。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import asyncio

import httpx


async def client_reuse():
    # base_url + 共用標頭設定一次，之後請求只寫相對路徑
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        headers={"User-Agent": "MyApp/1.0"},
    ) as client:
        r1 = await client.get("/users/me")  # 單元二 2.4
        r2 = await client.get("/api/v1/images")  # 單元四列表
    print("users/me：", r1.json())
    print("images 筆數：", len(r2.json()))
    return r1, r2


if __name__ == "__main__":
    asyncio.run(client_reuse())
