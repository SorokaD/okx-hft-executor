FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
COPY domain ./domain
COPY strategy ./strategy
COPY execution ./execution
COPY risk ./risk
COPY exchange ./exchange
COPY persistence ./persistence
COPY accounting ./accounting
COPY services ./services
COPY observability ./observability
COPY control ./control

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[control]"

RUN mkdir -p /app/data && chown -R app:app /app

USER app

ENTRYPOINT ["python", "-m", "app.main"]
