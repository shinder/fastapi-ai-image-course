"""串接外部公開 API（教材 7.4、附錄 C）

用的都是免費、不需註冊、不需 API Key 的公開服務，課堂上可以直接跑：

- Lorem Picsum  https://picsum.photos/     直接回一張隨機圖片（會先 302 轉址）
- Dog CEO       https://dog.ceo/api/       回 JSON，裡面才是圖片網址
- Postman Echo  https://postman-echo.com/  回聲服務，把你送出的東西原樣回傳

requests 是同步的，在 async def 路由裡呼叫一定要用 run_in_threadpool 包起來，
否則會卡住事件迴圈；httpx 則有原生的非同步版本，可以直接 await（附錄 C）。
"""

import asyncio

import httpx
import requests

# 隨機圖片（一次就給你檔案）
PICSUM_URL = "https://picsum.photos/800/600"
# 隨機狗狗圖片（兩段式：先給網址，再自己去抓）
DOG_API_URL = "https://dog.ceo/api/breeds/image/random"


def fetch_random_image(timeout: int = 15) -> tuple[bytes, str]:
    """從 Lorem Picsum 抓一張隨機圖片，回傳 (二進位內容, 檔名)。

    教材 7.4。注意幾件事：
    - 一定要設 timeout，否則對方卡住你也跟著卡
    - 圖片要用 r.content（二進位）而不是 r.text（會變亂碼）
    - Picsum 會回 302 轉址，requests 預設自動跟隨，
      所以 r.status_code 是 200，真正的 302 留在 r.history
    """
    try:
        r = requests.get(PICSUM_URL, timeout=timeout)
        r.raise_for_status()  # 4xx/5xx 轉成 HTTPError
    except requests.Timeout:
        raise RuntimeError("外部服務逾時")
    except requests.HTTPError as e:
        raise RuntimeError(f"外部服務錯誤：{e.response.status_code}")
    except requests.RequestException as e:
        # 連線失敗、DNS 錯誤等的後援（須放最後，因前面都是它的子類）
        raise RuntimeError(f"外部服務連線失敗：{e}")

    return r.content, "picsum.jpg"


def fetch_random_dog(timeout: int = 15) -> tuple[bytes, str]:
    """兩段式範例：先取 JSON 拿到圖片網址，再把圖片抓下來（教材 7.4）。

    很多圖庫與 CDN 型的服務都是這種設計：JSON 很小、可以快取，圖片才是大檔。
    """
    try:
        meta = requests.get(DOG_API_URL, timeout=timeout).json()
        image_url = meta["message"]
        r = requests.get(image_url, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"取得圖片失敗：{e}")
    except (KeyError, ValueError) as e:
        # 對方改了回應格式時，錯誤訊息要看得懂
        raise RuntimeError(f"回應格式不如預期：{e}")

    filename = image_url.rsplit("/", 1)[-1] or "dog.jpg"
    return r.content, filename


def import_random_image(api_base: str = "http://localhost:8000", timeout: int = 30) -> dict:
    """抓一張公開圖片，再上傳到自己的 API（教材 7.4 的綜合範例）。

    這就是實務上最常見的情境：從別的服務取得資料，存進自己的系統。
    """
    content, filename = fetch_random_image()
    files = {"file": (filename, content, "image/jpeg")}
    r = requests.post(f"{api_base}/api/v1/images/upload-only", files=files, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ---------- 附錄 C：httpx 的非同步版本 ----------


async def fetch_random_image_async(timeout: int = 15) -> tuple[bytes, str]:
    """與 fetch_random_image 相同，但用 httpx 的非同步用戶端。

    在 async def 路由裡可以直接 await，不需要 run_in_threadpool。
    注意 httpx 預設「不」跟隨轉址，要自己開 follow_redirects=True——
    這是它與 requests 最容易踩到的行為差異。
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(PICSUM_URL)
            r.raise_for_status()
    except httpx.TimeoutException:
        raise RuntimeError("外部服務逾時")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"外部服務錯誤：{e.response.status_code}")
    except httpx.RequestError as e:
        # 連線失敗、DNS 錯誤等的後援（須放最後，TimeoutException 等都是它的子類）
        raise RuntimeError(f"外部服務連線失敗：{e}")

    return r.content, "picsum.jpg"


async def fetch_many_async(count: int = 3, timeout: int = 20) -> list[int]:
    """並行抓多張圖，回傳每張的位元組數（教材 附錄 C）。

    asyncio.gather 讓多個請求同時進行——總耗時接近「最慢的那一個」，
    而不是全部加起來。return_exceptions=True 讓單一失敗不會拖垮整批。
    """
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        results = await asyncio.gather(
            *[client.get(PICSUM_URL) for _ in range(count)],
            return_exceptions=True,
        )
    return [len(r.content) if hasattr(r, "content") else -1 for r in results]
