"""Pytest fixtures for dramatiq-gcpubsub tests."""

import os
import uuid
from collections.abc import Iterator

import dramatiq
import pytest
from dramatiq.middleware import AgeLimit, Callbacks, Pipelines, Retries, TimeLimit

from dramatiq_gcpubsub import PubSubBroker


def _emulator_client_options():
    """Client options to connect to Pub/Sub emulator when PUBSUB_EMULATOR_HOST is set."""
    host = os.environ.get("PUBSUB_EMULATOR_HOST")
    if not host:
        return {}
    from google.api_core.client_options import ClientOptions

    return {"client_options": ClientOptions(api_endpoint=host)}


@pytest.fixture
def broker() -> Iterator[PubSubBroker]:
    """Create a PubSubBroker connected to the emulator (or real GCP if env not set)."""
    project_id = os.environ.get("PUBSUB_PROJECT_ID", "test-project")
    client_opts = _emulator_client_options()
    broker = PubSubBroker(
        project_id=project_id,
        middleware=[
            AgeLimit(),
            TimeLimit(),
            Callbacks(),
            Pipelines(),
            Retries(min_backoff=1000, max_backoff=900000, max_retries=96),
        ],
        publisher_options=client_opts,
        subscriber_options=client_opts,
    )
    dramatiq.set_broker(broker)
    yield broker
    broker.close()


@pytest.fixture
def queue_name(broker: PubSubBroker) -> str:
    """Unique queue name per test."""
    return f"queue_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def worker(broker: PubSubBroker):
    """Start a Dramatiq worker for the broker."""
    worker = dramatiq.Worker(broker)
    worker.start()
    yield worker
    worker.stop()
