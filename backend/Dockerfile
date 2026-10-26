FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app ./app
RUN python -m pip install --no-cache-dir uv==0.13.5 \
    && uv sync --frozen --no-dev \
    && useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
