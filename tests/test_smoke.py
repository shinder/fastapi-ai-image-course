"""最簡冒煙測試。

執行：
    uv run pytest

注意：許多端點需要 PostgreSQL 與 Redis，本檔僅測試不依賴外部服務的路由，
並透過直接建構 TestClient（不進入 with-context）跳過 lifespan 中的 init_db。
"""
from fastapi.testclient import TestClient


def test_health():
    from app.main import app

    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root():
    from app.main import app

    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200


def test_demo_create_image_validation():
    """教材 3.2 驗證範例：title 不可為空字串"""
    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/demo/images",
        json={"title": "", "url": "https://example.com/x.jpg"},
    )
    assert r.status_code == 422
