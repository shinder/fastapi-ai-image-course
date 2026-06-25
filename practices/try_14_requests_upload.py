"""requests 範例 14：上傳檔案（multipart）

對應教材 5.3（單元五 API 串接）
對應後端：POST /api/v1/images/upload（教材 4.7）

重點：
- files=：以 multipart/form-data 送出檔案，對應後端的 UploadFile = File(...)。
- files 的值是 (檔名, 檔案物件, MIME 型別) 的 tuple。
- data=：可同時夾帶一般表單欄位（這裡的 title），對應後端的 Form(...)。
- files 字典的 key（"file"）必須和後端路由參數名一致。

執行前請先啟動後端：
    uvicorn app.main:app --reload
（並準備一張圖片，預設讀 test_images/cat.jpg）
"""

import requests

URL = "http://localhost:8000/api/v1/images/upload"
IMAGE_PATH = "test_images/cat.jpg"


def upload_file():
    with open(IMAGE_PATH, "rb") as f:
        files = {"file": ("cat.jpg", f, "image/jpeg")}  # (檔名, 檔案物件, MIME)
        data = {"title": "我的貓"}  # 一般表單欄位
        r = requests.post(URL, files=files, data=data)
    print("狀態碼：", r.status_code)
    print("回應：", r.json())
    return r


if __name__ == "__main__":
    upload_file()
