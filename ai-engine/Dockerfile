FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app && mkdir -p /app/artifacts && chown app:app /app/artifacts
COPY --chown=app:app . .
USER app
RUN python -m training.train_anomaly
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health/live')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
