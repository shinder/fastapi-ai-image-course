FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

# --no-sync：不要在容器啟動時重新同步環境。uv run 預設會先 sync，而 dev 群組預設啟用，
# 會把上面 --no-dev 排除掉的 pytest / ruff 等又裝回來（無外網時直接啟動失敗）
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
