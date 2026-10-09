"""守住 src 佈局（教材 2.2）的幾個約定。

執行：
    uv run pytest tests/test_layout.py

這次改成 uv init 預設的 src 佈局之後，有三件事是「跑得起來」靠的，但平常不會被注意到：
  1. my_fastapi 是以可編輯模式裝進 .venv 的套件，不是靠「剛好在專案根目錄執行」才找得到
  2. 套件裡的 static/ 與 templates/ 用 Path(__file__) 推算，換個工作目錄也找得到
  3. uv run my-fastapi 的進入點（serve）會以 8080 埠啟動 main.py 裡的 app
與 test_smoke.py 一樣：直接建構 TestClient、不進 with，跳過 lifespan；不依賴任何外部服務。
"""

from importlib.metadata import entry_points
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_package_is_installed_from_src():
    """套件來自 src/my_fastapi，而且是 pyproject [build-system] 裝進 .venv 的發行版"""
    import my_fastapi

    assert (
        Path(my_fastapi.__file__).resolve() == PROJECT_ROOT / "src" / "my_fastapi" / "__init__.py"
    )

    # [project.scripts] 真的有登錄：uv run my-fastapi → my_fastapi:serve
    (ep,) = entry_points(group="console_scripts", name="my-fastapi")
    assert ep.value == "my_fastapi:serve"


def test_static_and_templates_do_not_depend_on_cwd(monkeypatch, tmp_path):
    """換到別的工作目錄後，/static 與 Jinja2 樣板仍找得到（路徑以套件位置為基準）。

    注意 /uploads 與 /models 刻意不在此測：它們指向專案根目錄的 uploads/ 與 ml_models/，
    由 .env 用相對路徑指定，本來就要求在專案根目錄啟動。"""
    from my_fastapi.main import app

    client = TestClient(app)
    monkeypatch.chdir(tmp_path)  # 從這一行起，任何相對路徑都會指到暫存資料夾

    r = client.get("/static/app.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]

    r = client.get("/static/demos/H04-hands-live.html")
    assert r.status_code == 200

    # /web/upload 只渲染樣板、不查資料庫；頁面裡 base.html 以 url_for 反查 /static 的網址
    r = client.get("/web/upload")
    assert r.status_code == 200
    assert "/static/app.css" in r.text


def test_serve_entry_point_is_not_shadowed_by_main_module():
    """進入點函式不可叫 main()：import my_fastapi.main 之後，my_fastapi.main 會變成子模組。

    這個測試先 import 子模組再取 serve，確保兩者可以並存。"""
    import my_fastapi
    import my_fastapi.main  # noqa: F401  刻意先載入子模組

    assert callable(my_fastapi.serve)
    # 反例：uv init 給的 main() 名稱在這裡會是模組，不是函式
    assert not callable(my_fastapi.main)


def test_serve_runs_uvicorn_on_dev_port(monkeypatch):
    """uv run my-fastapi 應以字串匯入路徑、8080 埠、reload 啟動；不真的開伺服器，攔下 uvicorn.run"""
    import uvicorn

    import my_fastapi

    called: dict = {}

    def fake_run(app, **kwargs):
        called["app"] = app
        called.update(kwargs)

    monkeypatch.setattr(uvicorn, "run", fake_run)
    my_fastapi.serve()

    assert called["app"] == "my_fastapi.main:app"
    assert called["port"] == my_fastapi.DEV_PORT == 8080
    assert called["reload"] is True


def test_dev_port_is_consistent_across_launchers():
    """start.bat 與 Dockerfile 寫死的埠號要和 DEV_PORT 一致（三處要一起改）"""
    import my_fastapi

    port = str(my_fastapi.DEV_PORT)
    assert f"--port {port}" in (PROJECT_ROOT / "start.bat").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert f"EXPOSE {port}" in dockerfile
    assert f'"--port", "{port}"' in dockerfile
