"""串接外部 AI API（教材 7.5、7.6）

requests 是同步、httpx 提供同步與非同步。
FastAPI 路由內推薦用 httpx.AsyncClient；獨立腳本則 requests 即可。
"""
import asyncio

import httpx
import requests

from app.config import settings

EXTERNAL_AI_URL = "https://ai.thirdparty.com/v1/classify"


def call_external_classify(content: bytes) -> dict:
    """同步版（教材 7.5）"""
    files = {"file": ("img.jpg", content, "image/jpeg")}
    headers = {"X-API-Key": settings.OPENAI_API_KEY}
    try:
        r = requests.post(
            EXTERNAL_AI_URL,
            files=files,
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.Timeout:
        raise RuntimeError("外部 AI 服務逾時")
    except requests.HTTPError as e:
        raise RuntimeError(f"外部 AI 錯誤：{e.response.status_code}")
    except requests.RequestException as e:
        # 連線失敗、DNS 錯誤等其餘 requests 例外的兜底（須放最後，因前面都是它的子類）
        raise RuntimeError(f"外部 AI 連線失敗：{e}")


async def call_external_classify_async(content: bytes) -> dict:
    """非同步版（教材 7.6）"""
    files = {"file": ("img.jpg", content, "image/jpeg")}
    headers = {"X-API-Key": settings.OPENAI_API_KEY}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(EXTERNAL_AI_URL, files=files, headers=headers)
        r.raise_for_status()
        return r.json()


async def call_multiple(content: bytes, urls: list[str]) -> dict:
    """並行呼叫多個 API（教材 7.6）"""
    async with httpx.AsyncClient(timeout=30) as client:
        results = await asyncio.gather(
            *[client.post(u, files={"file": ("i.jpg", content)}) for u in urls],
            return_exceptions=True,
        )
    return {
        "results": [r.json() if hasattr(r, "json") else str(r) for r in results]
    }
