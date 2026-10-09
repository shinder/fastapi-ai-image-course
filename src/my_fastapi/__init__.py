"""my_fastapi 套件（教材 2.2）：整個後端都在這個套件裡。

`uv init` 採用 src 佈局，會產生 src/my_fastapi/__init__.py 與一個 main()，
`uv sync` 時把這個套件以可編輯模式裝進 .venv，所以：
  - 不管從哪個目錄執行、測試放在哪裡，`from my_fastapi.xxx import ...` 都找得到
  - pyproject.toml 的 [project.scripts] 把 `uv run my-fastapi` 指到下面的 serve()

為什麼不沿用 uv init 給的名字 main()：本套件的 FastAPI 入口是 main.py，
而 Python 在 import my_fastapi.main（子模組）之後，會把它綁到 my_fastapi.main
這個屬性上，把同名的 main() 函式蓋掉；任何先 import 過 main.py 的程式再呼叫
my_fastapi.main() 就會變成「呼叫模組」而出錯。改用 serve() 就沒有這個衝突。

啟動開發伺服器（擇一）：
    uv run fastapi dev src/my_fastapi/main.py --port 8080   # fastapi CLI，含自動重載
    uv run my-fastapi                                       # 走這裡的 serve()，效果相同
"""

# 開發伺服器的埠號；start.bat 與 Dockerfile 也用同一個值，改的時候三處一起改
DEV_PORT = 8080


def serve() -> None:
    """`uv run my-fastapi` 的進入點：直接以 uvicorn 啟動 main.py 裡的 app。"""
    # 放在函式內 import：單純 `import my_fastapi` 時不必載入伺服器
    import uvicorn

    # 傳字串而不是 app 物件，reload 才能在改檔後重新 import
    uvicorn.run("my_fastapi.main:app", host="0.0.0.0", port=DEV_PORT, reload=True)
