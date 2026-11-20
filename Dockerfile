FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src

RUN uv sync --no-dev

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev crm-system-informatika"]