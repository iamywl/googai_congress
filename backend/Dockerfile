# syntax=docker/dockerfile:1
# ---- Builder: resolve dependencies into an isolated virtualenv -------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- Runtime: minimal, non-root image carrying only the venv + app ---------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY pyproject.toml ./

# Run as an unprivileged user (non-root security context).
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER 10001

EXPOSE 8080

# Cloud Run injects $PORT; honour it, defaulting to 8080 locally.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
