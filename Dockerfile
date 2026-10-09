FROM python:3.12-slim

WORKDIR /app

# 先只複製相依描述檔，讓「裝第三方套件」這一層能被 Docker 快取：
# 之後只改程式碼時不必重裝套件。
# --no-install-project：pyproject.toml 有 [build-system]，uv sync 預設會連專案本身
# （src/my_fastapi）一起建置安裝，但這時 src/ 還沒複製進來，先跳過。
COPY pyproject.toml uv.lock README.md ./
RUN pip install uv && uv sync --frozen --no-dev --no-install-project

# 再複製整個專案，並把 my_fastapi 套件本身裝進 .venv（這一步很快，沒有外部下載）。
# .dockerignore 已排除 .venv、.env、uploads/ 等不該進映像的東西。
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8080

# --no-sync：不要在容器啟動時重新同步環境。uv run 預設會先 sync，而 dev 群組預設啟用，
# 會把上面 --no-dev 排除掉的 pytest / ruff 等又裝回來（無外網時直接啟動失敗）
CMD ["uv", "run", "--no-sync", "uvicorn", "my_fastapi.main:app", \
     "--host", "0.0.0.0", "--port", "8080"]
