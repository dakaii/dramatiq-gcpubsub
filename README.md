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

## Running tests

**Unit tests** (no emulator):

```bash
pytest tests/unit/ -v
```

**Integration tests** (require Pub/Sub emulator):

```bash
# Start emulator and run all tests
docker compose up --build

# Or start emulator only, then run tests locally
docker compose up -d pubsub-emulator
export PUBSUB_EMULATOR_HOST=localhost:8085
export PUBSUB_PROJECT_ID=test-project
pytest tests/ -v
```

## Publishing to PyPI

To create the GitHub repo and publish releases to PyPI (using trusted publishing, no tokens in the repo), see [docs/PUBLISHING.md](docs/PUBLISHING.md).

## License

Apache 2.0
