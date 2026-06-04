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


# ---------- 單元八 網頁與樣版（補充教材，Jinja2）----------


def test_web_gallery_page():
    """8.6 圖片列表頁：應回 200 並渲染出 HTML（含「圖片列表」標題）"""
    from app.main import app

    client = TestClient(app)
    r = client.get("/web")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "圖片列表" in r.text


def test_web_upload_page():
    """8.6 上傳表單頁：應回 200 並含 file 上傳欄位"""
    from app.main import app

    client = TestClient(app)
    r = client.get("/web/upload")
    assert r.status_code == 200
    assert 'name="file"' in r.text


def test_web_upload_prg(tmp_path, monkeypatch):
    """8.6 PRG 上傳：POST 後應回 303 並 Location 指向列表頁。

    用 tmp_path 覆蓋上傳目錄，避免污染真正的 uploads/。
    """
    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    # 最小合法 PNG（1x1）位元組
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    client = TestClient(app)
    # follow_redirects=False 才能驗證 303 本身（否則會自動跟著導向）
    r = client.post(
        "/web/upload",
        files={"file": ("x.png", png, "image/png")},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"].endswith("/web")
    # 檔案確實寫進了被覆蓋的上傳目錄
    assert len(list(tmp_path.iterdir())) == 1
