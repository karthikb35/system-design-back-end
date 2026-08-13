# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
# Users gRPC service image.
#
# IMPORTANT: this image is built with the *repository root* as the build context
# (see docker-compose.yml) so it can COPY the shared `protos/` directory and
# regenerate the stubs from the single source of truth at build time.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1) Dependencies (cached until requirements change)
COPY services/users/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Application source
COPY services/users/app ./app

# 3) Regenerate gRPC stubs from the canonical protos (overwrites any stale copy)
COPY protos /protos
RUN python -m grpc_tools.protoc -I/protos \
        --python_out=app/pb --grpc_python_out=app/pb \
        /protos/users.proto

# 4) Non-root user
RUN useradd --create-home --uid 1001 appuser
USER appuser

EXPOSE 50051

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD ["python", "-m", "app.healthcheck"]

CMD ["python", "-m", "app.server"]
