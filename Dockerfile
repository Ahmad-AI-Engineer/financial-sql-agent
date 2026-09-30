# ============================================================
# Financial SQL Agent — Streamlit UI + agent (one program).
# Built and run by docker-compose.yml alongside the postgres service.
# ============================================================
# NOT python:3.11-slim: the slim variants fail with "exec format error" on
# this Docker Desktop install, same as postgres:16 did. Full image works.
FROM python:3.11

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first: Docker caches this layer, so later code
# changes rebuild in seconds instead of re-downloading every package.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then the project code (see .dockerignore for what stays out).
COPY . .

# Run as an unprivileged user. Compose stores its generated schema in runtime/.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/runtime \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

# 0.0.0.0 is required — the default (localhost) would only be reachable
# from inside the container, so your browser could never see the UI.
CMD ["sh", "-c", "exec streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
