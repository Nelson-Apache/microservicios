# ─── Stage 1: Builder ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /app/venv /app/venv
COPY main.py .
COPY app/ ./app/

ENV PATH="/app/venv/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
