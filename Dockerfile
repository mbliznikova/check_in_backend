# ── Stage 1: build ─────────────────────────────────────────────
FROM python:3.12-slim AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: production ─────────────────────────────────────────
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=check_in_backend.settings_production \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

COPY . .

# Placeholder values let settings_production.py import without error at build
# time. Actual secrets are injected at runtime and never touch the filesystem.
RUN DJANGO_SECRET_KEY=placeholder \
    DB_NAME=placeholder \
    DB_USER=placeholder \
    DB_PASSWORD=placeholder \
    REDIS_URL=redis://placeholder \
    CLERK_JWKS_URL=https://placeholder.example.com/.well-known/jwks.json \
    CLERK_ISSUER=https://placeholder.example.com \
    CLERK_AUDIENCE=placeholder \
    python manage.py collectstatic --noinput

RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE $PORT

CMD ["gunicorn", "check_in_backend.wsgi:application", \
     "--workers", "2", \
     "--threads", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--access-logfile", "-"]
