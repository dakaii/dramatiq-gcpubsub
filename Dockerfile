FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY src ./src
COPY tests ./tests

CMD ["pytest", "tests/", "-v", "--cov=src/dramatiq_gcpubsub", "--cov-report=term-missing"]
