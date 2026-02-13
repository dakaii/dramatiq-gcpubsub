# dramatiq-gcpubsub

A [Dramatiq](https://dramatiq.io/) broker for [Google Cloud Pub/Sub](https://cloud.google.com/pubsub).

## Installation

```bash
pip install dramatiq-gcpubsub
```

## Usage

```python
import dramatiq
from dramatiq_gcpubsub import PubSubBroker

broker = PubSubBroker(project_id="your-gcp-project-id")
dramatiq.set_broker(broker)

@dramatiq.actor
def my_task(x, y):
    return x + y

my_task.send(3, 7)
```

## Local development with the emulator

Set the emulator host and project, then run your worker:

```bash
export PUBSUB_EMULATOR_HOST=localhost:8085
export PUBSUB_PROJECT_ID=test-project
dramatiq myapp.tasks
```

Start the Pub/Sub emulator (e.g. with Docker):

```bash
docker run --rm -p 8085:8085 gcr.io/google.com/cloudsdktool/cloud-sdk:latest \
  gcloud beta emulators pubsub start --project=test-project --host-port=0.0.0.0:8085
```

## Limitations and future work

- **Delayed messages** — `enqueue(..., delay=...)` is not supported yet; calling it raises `NotImplementedError`. Planned: use Pub/Sub scheduled publish (`publish_time`).
- **Dead-letter topic** — Subscriptions are created without a dead-letter policy. Planned: optional broker parameter to attach a dead-letter topic to subscriptions.
- **Publish batching** — Messages are published one at a time. Planned: optional batching for higher throughput.

## GCP permissions

For production, the service account used by your worker needs at least:

- `pubsub.topics.create`, `pubsub.topics.publish`
- `pubsub.subscriptions.create`, `pubsub.subscriptions.consume`, `pubsub.subscriptions.update`

Or use the predefined role `roles/pubsub.admin` for full access.

## Testing (no real GCP needed)

You do **not** need a real GCP project or Pub/Sub for testing. Use the **Pub/Sub emulator** for all local and CI testing. Real GCP is only for production.

### 1. Unit tests (no emulator)

Fast, mocked; no Docker or GCP:

```bash
pytest tests/unit/ -v
```

### 2. Integration tests (with emulator)

These hit the real Pub/Sub API against the emulator (enqueue, consume, ack, requeue).

**Option A – run everything in Docker:**

```bash
docker compose up --build
```

**Option B – emulator in Docker, tests on your machine:**

```bash
# Terminal 1: start emulator
docker compose up pubsub-emulator

# Terminal 2: run tests (wait for emulator to be ready, then)
export PUBSUB_EMULATOR_HOST=localhost:8085
export PUBSUB_PROJECT_ID=test-project
pytest tests/ -v
```

Integration tests are skipped if `PUBSUB_EMULATOR_HOST` is not set.

### 3. Manual smoke test (optional)

From the project root, run the emulator, a worker, and send one task (see `examples/smoke_test.py`):

```bash
# Terminal 1: start emulator
docker run --rm -p 8085:8085 gcr.io/google.com/cloudsdktool/cloud-sdk:latest \
  gcloud beta emulators pubsub start --project=test-project --host-port=0.0.0.0:8085

# Terminal 2: start worker (from project root)
export PUBSUB_EMULATOR_HOST=localhost:8085 PUBSUB_PROJECT_ID=test-project
PYTHONPATH=. dramatiq examples.smoke_test

# Terminal 3: send a task
export PUBSUB_EMULATOR_HOST=localhost:8085 PUBSUB_PROJECT_ID=test-project
python -c "from examples.smoke_test import add; add.send(3, 7); print('Sent. Check worker terminal.')"
```

You should see `add(3, 7) = 10` in the worker terminal.

## Publishing to PyPI

To create the GitHub repo and publish releases to PyPI (using trusted publishing, no tokens in the repo), see [docs/PUBLISHING.md](docs/PUBLISHING.md).

## License

Apache 2.0
