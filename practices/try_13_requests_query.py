"""requests 範例 13：查詢參數、自訂標頭、Cookie、逾時

對應教材 5.3（單元五 API 串接）
對應後端：GET /api/v1/images（列表，支援 keyword / limit，教材 4.6）

重點：
- params=：自動把 dict 組成查詢字串（?keyword=cat&limit=10），不必自己拼接 URL。
- headers=：帶自訂標頭（例如 User-Agent；認證標頭見 try_17）。
- cookies=：帶 cookie。
- timeout=：逾時秒數，務必設定。
- 可印 r.url 觀察 params 實際組成的查詢字串。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import requests

URL = "http://localhost:8000/api/v1/images"


def with_query_headers_cookies():
    r = requests.get(
        URL,
        params={"keyword": "cat", "limit": 10},  # 會組成 ?keyword=cat&limit=10
        headers={"User-Agent": "MyApp/1.0"},  # 自訂標頭
        cookies={"session": "xyz"},  # 帶 cookie
        timeout=10,  # 逾時秒數
    )
    print("實際請求的 URL：", r.url)  # 觀察 params 組成的查詢字串
    print("結果筆數：", len(r.json()))
    return r


if __name__ == "__main__":
    with_query_headers_cookies()
