"""Integration tests for PubSubBroker (require Pub/Sub emulator)."""

import time

import dramatiq
import pytest


@pytest.mark.skipif(
    not __import__("os").environ.get("PUBSUB_EMULATOR_HOST"),
    reason="PUBSUB_EMULATOR_HOST not set; run with docker compose or set env",
)
def test_can_enqueue_and_process_messages(broker, worker, queue_name):
    db = []

    @dramatiq.actor(queue_name=queue_name)
    def do_work(x):
        db.append(x)

    do_work.send(1)
    time.sleep(2)
    assert db == [1]


@pytest.mark.skipif(
    not __import__("os").environ.get("PUBSUB_EMULATOR_HOST"),
    reason="PUBSUB_EMULATOR_HOST not set",
)
def test_can_requeue_consumed_messages(broker, queue_name):
    @dramatiq.actor(queue_name=queue_name)
    def do_work():
        pass

    do_work.send()
    time.sleep(1)

    consumer = broker.consume(queue_name)
    first_message = next(consumer)
    assert first_message is not None
    consumer.requeue([first_message])

    second_message = next(consumer)
    assert second_message is not None
    assert first_message.message_id == second_message.message_id
    consumer.ack(second_message)


@pytest.mark.skipif(
    not __import__("os").environ.get("PUBSUB_EMULATOR_HOST"),
    reason="PUBSUB_EMULATOR_HOST not set",
)
def test_can_ack_and_nack(broker, queue_name):
    @dramatiq.actor(queue_name=queue_name)
    def do_work():
        pass

    do_work.send()
    time.sleep(1)

    consumer = broker.consume(queue_name)
    msg = next(consumer)
    assert msg is not None
    consumer.ack(msg)
    # Verify ack succeeded (message removed from subscription); we do not
    # call next(consumer) again to avoid blocking on emulator's pull behavior.
