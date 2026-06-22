"""OpenAI DALL·E 影像生成（教材 5.6）

需安裝可選依賴：
    uv sync --extra openai
並在 .env 設定 OPENAI_API_KEY。
"""

from app.config import settings


def generate_image(prompt: str) -> str:
    """產生圖片並回傳 URL"""
    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url
