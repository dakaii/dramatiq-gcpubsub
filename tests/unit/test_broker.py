"""Unit tests for PubSubBroker (mocked Pub/Sub)."""

from unittest.mock import MagicMock, patch

import dramatiq
import pytest

from dramatiq_gcpubsub import PubSubBroker


@patch("dramatiq_gcpubsub.pubsub_broker.pubsub_v1")
def test_declare_queue_creates_topic_and_subscription(mock_pubsub_v1):
    publisher = MagicMock()
    publisher.topic_path.return_value = "projects/test-project/topics/dramatiq-default"
    subscriber = MagicMock()
    subscriber.subscription_path.return_value = (
        "projects/test-project/subscriptions/dramatiq-default-sub"
    )
    mock_pubsub_v1.PublisherClient.return_value = publisher
    mock_pubsub_v1.SubscriberClient.return_value = subscriber

    broker = PubSubBroker(project_id="test-project")
    broker.declare_queue("default")

    assert "default" in broker.queues
    publisher.create_topic.assert_called_once()
    call = publisher.create_topic.call_args
    assert call.kwargs["request"]["name"] == "projects/test-project/topics/dramatiq-default"

    subscriber.create_subscription.assert_called_once()
    call = subscriber.create_subscription.call_args
    req = call.kwargs["request"]
    assert req["name"] == "projects/test-project/subscriptions/dramatiq-default-sub"
    assert req["topic"] == "projects/test-project/topics/dramatiq-default"


@patch("dramatiq_gcpubsub.pubsub_broker.pubsub_v1")
def test_declare_queue_idempotent(mock_pubsub_v1):
    publisher = MagicMock()
    publisher.topic_path.return_value = "projects/test-project/topics/dramatiq-default"
    subscriber = MagicMock()
    subscriber.subscription_path.return_value = (
        "projects/test-project/subscriptions/dramatiq-default-sub"
    )
    mock_pubsub_v1.PublisherClient.return_value = publisher
    mock_pubsub_v1.SubscriberClient.return_value = subscriber

    broker = PubSubBroker(project_id="test-project")
    broker.declare_queue("default")
    broker.declare_queue("default")

    publisher.create_topic.assert_called_once()
    subscriber.create_subscription.assert_called_once()


@patch("dramatiq_gcpubsub.pubsub_broker.pubsub_v1")
def test_enqueue_publishes_encoded_message(mock_pubsub_v1):
    publisher = MagicMock()
    publisher.topic_path.return_value = "projects/test-project/topics/dramatiq-default"
    subscriber = MagicMock()
    mock_pubsub_v1.PublisherClient.return_value = publisher
    mock_pubsub_v1.SubscriberClient.return_value = subscriber

    broker = PubSubBroker(project_id="test-project")
    broker.queues["default"] = "projects/test-project/subscriptions/dramatiq-default-sub"
    dramatiq.set_broker(broker)

    @dramatiq.actor(queue_name="default")
    def noop():
        pass

    message = noop.message()
    broker.enqueue(message)

    publisher.publish.assert_called_once()
    call = publisher.publish.call_args
    topic_path, data = call.args
    assert topic_path == "projects/test-project/topics/dramatiq-default"
    assert isinstance(data, bytes)
    # Decode round-trip
    decoded = dramatiq.Message.decode(data)
    assert decoded.actor_name == "noop"
    assert decoded.queue_name == "default"


@patch("dramatiq_gcpubsub.pubsub_broker.pubsub_v1")
def test_enqueue_raises_queue_not_found_for_undeclared_queue(mock_pubsub_v1):
    mock_pubsub_v1.PublisherClient.return_value = MagicMock()
    mock_pubsub_v1.SubscriberClient.return_value = MagicMock()

    broker = PubSubBroker(project_id="test-project")
    # Do not declare the queue; create message manually so declare_actor is not called
    message = dramatiq.Message(
        queue_name="unknown",
        actor_name="noop",
        args=(),
        kwargs={},
        options={},
        message_id="test-id",
        message_timestamp=0,
    )
    with pytest.raises(dramatiq.QueueNotFound):
        broker.enqueue(message)


@patch("dramatiq_gcpubsub.pubsub_broker.pubsub_v1")
def test_enqueue_delayed_raises_not_implemented(mock_pubsub_v1):
    mock_pubsub_v1.PublisherClient.return_value = MagicMock()
    mock_pubsub_v1.SubscriberClient.return_value = MagicMock()

    broker = PubSubBroker(project_id="test-project")
    broker.queues["default"] = "projects/test-project/subscriptions/dramatiq-default-sub"
    dramatiq.set_broker(broker)

    @dramatiq.actor(queue_name="default")
    def noop():
        pass

    message = noop.message()
    with pytest.raises(NotImplementedError):
        broker.enqueue(message, delay=5000)


@patch("dramatiq_gcpubsub.pubsub_broker.pubsub_v1")
def test_consume_raises_queue_not_found_for_undeclared_queue(mock_pubsub_v1):
    mock_pubsub_v1.PublisherClient.return_value = MagicMock()
    mock_pubsub_v1.SubscriberClient.return_value = MagicMock()

    broker = PubSubBroker(project_id="test-project")
    with pytest.raises(dramatiq.QueueNotFound):
        broker.consume("unknown")


@patch("dramatiq_gcpubsub.pubsub_broker.pubsub_v1")
def test_get_declared_queues(mock_pubsub_v1):
    mock_pubsub_v1.PublisherClient.return_value = MagicMock()
    mock_pubsub_v1.SubscriberClient.return_value = MagicMock()

    broker = PubSubBroker(project_id="test-project")
    assert broker.get_declared_queues() == set()

    broker.queues["default"] = "sub-path"
    broker.queues["high"] = "sub-path-2"
    assert broker.get_declared_queues() == {"default", "high"}
