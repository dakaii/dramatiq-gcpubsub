"""
Smoke test: enqueue a task and process it with the Pub/Sub emulator.

Usage:
  Terminal 1: start emulator
    docker run --rm -p 8085:8085 gcr.io/google.com/cloudsdktool/cloud-sdk:latest \
      gcloud beta emulators pubsub start --project=test-project --host-port=0.0.0.0:8085

  Terminal 2: start worker
    export PUBSUB_EMULATOR_HOST=localhost:8085 PUBSUB_PROJECT_ID=test-project
    dramatiq examples.smoke_test

  Terminal 3: send a task
    export PUBSUB_EMULATOR_HOST=localhost:8085 PUBSUB_PROJECT_ID=test-project
    python -c "from examples.smoke_test import add; add.send(3, 7); print('Sent. Check worker terminal.')"
"""
import dramatiq
from dramatiq_gcpubsub import PubSubBroker

broker = PubSubBroker(project_id="test-project")
dramatiq.set_broker(broker)


@dramatiq.actor
def add(x: int, y: int) -> int:
    result = x + y
    print(f"  add({x}, {y}) = {result}")
    return result
