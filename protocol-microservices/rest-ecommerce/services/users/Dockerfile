# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
# Users service image. Slim base, non-root user, dependency layer cached
# separately from source so code changes don't reinstall packages.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1) Install dependencies first (this layer is cached until requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy application source
COPY app ./app

# 3) Run as a non-root user (least privilege)
RUN useradd --create-home --uid 1001 appuser
USER appuser

EXPOSE 8001

# Uvicorn serves the FastAPI app; one worker per container (scale by replicas)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
