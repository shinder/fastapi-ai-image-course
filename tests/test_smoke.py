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


# ---------- 單元八 網頁與模板（補充教材，Jinja2）----------


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


# ---------- 單元九 MongoDB 留言（補充教材）----------
# 測試以 TestClient 直接建構（不進 lifespan），因此未呼叫 connect_mongo，
# Mongo client 維持 None，正好用來驗證「未連線時的優雅行為」。


def test_notes_validation():
    """缺必填欄位 text 時，應在進到 Mongo 之前就被擋下回 422"""
    from app.main import app

    client = TestClient(app)
    r = client.post("/api/v1/notes", json={"image_filename": "cat.jpg"})
    assert r.status_code == 422


def test_notes_requires_mongo():
    """未連線 MongoDB 時，建立留言應回 503（而非崩潰）"""
    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/notes",
        json={"image_filename": "cat.jpg", "text": "測試"},
    )
    assert r.status_code == 503


# ---------- 單元七進階：速率限制 / 分散式鎖（Redis 不可用時 fail-open）----------


def _raising_redis():
    """回傳一個所有操作都丟 RedisError 的假 client，模擬 Redis 不可用。

    用 mock 而非真的連不到的 port，測試才會即時（避免 redis-py 重試的延遲）。
    """
    from unittest.mock import MagicMock

    import redis

    m = MagicMock()
    m.incr.side_effect = redis.RedisError("down")
    m.set.side_effect = redis.RedisError("down")
    m.delete.side_effect = redis.RedisError("down")
    return m


def test_rate_limit_fail_open():
    """Redis 不可用時，限流應放行（不丟例外、不擋請求）"""
    from types import SimpleNamespace

    from app.services.rate_limit import RateLimit

    rl = RateLimit(limit=1, window=60)
    req = SimpleNamespace(client=SimpleNamespace(host="1.2.3.4"))
    for _ in range(5):
        assert rl(req, _raising_redis()) is None


def test_acquire_lock_fail_open():
    """Redis 不可用時，取鎖應 fail-open（視為取得，照常執行）"""
    from app.services.cache_service import acquire_lock

    with acquire_lock(_raising_redis(), "lock:x", ttl=5) as got:
        assert got is True
