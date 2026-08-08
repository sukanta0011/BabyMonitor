FROM python:3.12-slim
WORKDIR /app

RUN pip install uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgles2 \
    libegl1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY src/ ./src/
COPY face_detection_models/ ./face_detection_models/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]