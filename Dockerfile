FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY . .
RUN uv sync --no-dev --frozen || uv sync --no-dev
ENV PATH="/app/.venv/bin:$PATH"
CMD ["sh","-c","uvicorn gateway.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
