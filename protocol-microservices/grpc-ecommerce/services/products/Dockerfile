# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
# Products gRPC service image. Built with the REPOSITORY ROOT as the build
# context so it can COPY the shared `protos/` and regenerate stubs.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/products/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/products/app ./app

COPY protos /protos
RUN python -m grpc_tools.protoc -I/protos \
        --python_out=app/pb --grpc_python_out=app/pb \
        /protos/products.proto

RUN useradd --create-home --uid 1001 appuser
USER appuser

EXPOSE 50052

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD ["python", "-m", "app.healthcheck"]

CMD ["python", "-m", "app.server"]
