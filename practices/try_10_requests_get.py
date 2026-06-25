"""requests 範例 10：基本 GET 請求

對應教材 5.2（單元五 API 串接）
對應後端：GET /api/v1/images/{id}（取得單一圖片，教材 4.6）

重點：
- requests.get(url) 送出 GET 請求，回傳一個 Response 物件。
- Response 常用屬性：
  - .status_code：HTTP 狀態碼（200 成功、404 找不到…）
  - .headers：回應標頭（dict-like），可取 Content-Type 等
  - .text：回應主體的原始字串（未解析）
  - .json()：把 JSON 主體解析成 Python dict / list（非 JSON 會丟例外）

執行前請先啟動後端：
    uvicorn app.main:app --reload
（並確認資料庫裡有 id=1 的圖片，可先跑 try_11_requests_post.py 建立一筆）
"""

import requests

# 打本專案單元四的「取得單一圖片」端點
URL = "http://localhost:8000/api/v1/images/1"


def basic_get():
    r = requests.get(URL)
    print("狀態碼：", r.status_code)  # 200
    print("Content-Type：", r.headers["Content-Type"])  # application/json
    print("原始字串：", r.text)  # 未解析的 JSON 字串
    print("解析成 dict：", r.json())  # Python dict
    return r


if __name__ == "__main__":
    basic_get()
