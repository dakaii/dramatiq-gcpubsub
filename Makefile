.PHONY: up test test-unit test-integration lint install

# Start the Pub/Sub emulator only
up:
	docker compose up -d pubsub-emulator

# Run all tests (unit + integration) via Docker (emulator + test runner)
test:
	docker compose run --rm tests

# Run unit tests only (no Docker/emulator)
test-unit:
	pytest tests/unit/ -v --cov=src/dramatiq_gcpubsub --cov-report=term-missing

# Run integration tests only (requires PUBSUB_EMULATOR_HOST)
test-integration:
	pytest tests/integration/ -v

# Lint with ruff
lint:
	ruff check src tests
	ruff format --check src tests

# Install package in editable mode with dev deps
install:
	pip install -e ".[dev]"
