"""httpx 範例 24：上傳檔案（multipart，非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_14 的 requests 同步版。
對應後端：POST /api/v1/images/upload（教材 4.7）

重點：
- files= 的用法和 requests 一樣（multipart/form-data），改成 await client.post。
- files 的值是 (檔名, 檔案物件, MIME 型別) 的 tuple。
- data= 可同時夾帶一般表單欄位（這裡的 title），對應後端的 Form(...)。
- 開檔仍用一般 open（小檔即可）；只有「送請求」這段是非同步的。

執行前請先啟動後端：
    uvicorn app.main:app --reload
（並準備一張圖片，預設讀 test_images/cat.jpg）
"""

import asyncio

import httpx

URL = "http://localhost:8000/api/v1/images/upload"
IMAGE_PATH = "test_images/cat.jpg"


async def upload_file():
    with open(IMAGE_PATH, "rb") as f:
        files = {"file": ("cat.jpg", f, "image/jpeg")}  # (檔名, 檔案物件, MIME)
        data = {"title": "我的貓"}  # 一般表單欄位
        async with httpx.AsyncClient() as client:
            r = await client.post(URL, files=files, data=data)
    print("狀態碼：", r.status_code)
    print("回應：", r.json())
    return r


if __name__ == "__main__":
    asyncio.run(upload_file())
