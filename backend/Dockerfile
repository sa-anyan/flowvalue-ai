FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-orchestration.txt requirements-monte-carlo.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-monte-carlo.txt && useradd --create-home appuser
COPY . /app/backend
RUN mkdir -p /app/outputs && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn backend.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
