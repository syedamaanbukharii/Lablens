FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .
RUN useradd --create-home --uid 10001 lablens && mkdir -p /app/uploads && chown -R lablens:lablens /app
USER lablens
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -fsS http://localhost:8000/api/health || exit 1
CMD ["uvicorn", "lablens.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
