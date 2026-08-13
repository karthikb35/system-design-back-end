# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
# API Gateway image. HTTP (uvicorn) on the outside, gRPC client on the inside.
# Built with the REPOSITORY ROOT as the build context so it can COPY the shared
# `protos/` and regenerate ALL three services' stubs.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway/app ./app

COPY protos /protos
RUN python -m grpc_tools.protoc -I/protos \
        --python_out=app/pb --grpc_python_out=app/pb \
        /protos/users.proto /protos/products.proto /protos/orders.proto

RUN useradd --create-home --uid 1001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
