#Build the virtual environment
FROM python:3.12-slim-bookworm AS builder

RUN pip install poetry

ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root
##

RUN mkdir -p /app

ENV DT_HOST=0.0.0.0

COPY configs/ /app/configs/

COPY scripts/ /app/scripts/

COPY examples/ /app/examples/

COPY pyproject.toml README.md /app/

COPY src/ /app/src/

WORKDIR /app

RUN poetry install --no-interaction

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8010


CMD ["python", "src/digital_twin/main.py"]

