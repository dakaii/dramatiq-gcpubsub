"""Google Cloud Pub/Sub broker for Dramatiq."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Optional

import dramatiq
from dramatiq.logging import get_logger
from google.api_core import exceptions as gcp_exceptions
from google.cloud import pubsub_v1

if TYPE_CHECKING:
    from dramatiq import Message


def _topic_id(queue_name: str) -> str:
    return f"dramatiq-{queue_name.replace('_', '-')}"


def _subscription_id(queue_name: str) -> str:
    return f"dramatiq-{queue_name.replace('_', '-')}-sub"


class PubSubMessageProxy(dramatiq.MessageProxy):
    """Wrapper around a Pub/Sub received message."""

    def __init__(self, ack_id: str, subscription_path: str, message: dramatiq.Message) -> None:
        super().__init__(message)
        self._ack_id = ack_id
        self._subscription_path = subscription_path

    def ack(self, subscriber: pubsub_v1.SubscriberClient) -> None:
        """Acknowledge the message."""
        subscriber.acknowledge(
            request={
                "subscription": self._subscription_path,
                "ack_ids": [self._ack_id],
            }
        )

    def nack(self, subscriber: pubsub_v1.SubscriberClient) -> None:
        """Nack the message so it is redelivered."""
        subscriber.modify_ack_deadline(
            request={
                "subscription": self._subscription_path,
                "ack_ids": [self._ack_id],
                "ack_deadline_seconds": 0,
            }
        )


class PubSubConsumer(dramatiq.Consumer):
    """Consumer that pulls messages from a Pub/Sub subscription."""

    def __init__(
        self,
        subscriber: pubsub_v1.SubscriberClient,
        subscription_path: str,
        prefetch: int,
        timeout_ms: int,
    ) -> None:
        self.logger = get_logger(__name__, type(self))
        self._subscriber = subscriber
        self._subscription_path = subscription_path
        self._prefetch = max(1, min(prefetch, 100))  # Pub/Sub max is 1000, cap for sanity
        self._timeout_ms = timeout_ms
        self._messages: deque[PubSubMessageProxy] = deque()

    def __next__(self) -> PubSubMessageProxy | None:
        try:
            return self._messages.popleft()
        except IndexError:
            pass

        request = {
            "subscription": self._subscription_path,
            "max_messages": self._prefetch,
        }
        # Use a finite timeout so pull() does not block indefinitely (e.g. in tests).
        timeout_sec = max(1, self._timeout_ms // 1000) if self._timeout_ms else 30
        try:
            response = self._subscriber.pull(
                request=request,
                timeout=timeout_sec,
            )
        except Exception as e:
            self.logger.exception("Pull failed: %s", e)
            return None

        for received in response.received_messages:
            try:
                data = received.message.data
                if not isinstance(data, bytes):
                    data = data.encode("utf-8") if isinstance(data, str) else bytes(data)
                decoded = dramatiq.Message.decode(data)
                proxy = PubSubMessageProxy(
                    ack_id=received.ack_id,
                    subscription_path=self._subscription_path,
                    message=decoded,
                )
                self._messages.append(proxy)
            except Exception as e:
                self.logger.exception("Failed to decode message: %r", e)

        try:
            return self._messages.popleft()
        except IndexError:
            return None

    def ack(self, message: PubSubMessageProxy) -> None:
        message.ack(self._subscriber)

    def nack(self, message: PubSubMessageProxy) -> None:
        message.nack(self._subscriber)

    def requeue(self, messages: Iterable[PubSubMessageProxy]) -> None:
        for msg in messages:
            msg.nack(self._subscriber)


class PubSubBroker(dramatiq.Broker):
    """Dramatiq broker using Google Cloud Pub/Sub.

    Uses one topic per queue (e.g. queue \"default\" -> topic \"dramatiq-default\",
    subscription \"dramatiq-default-sub\"). Uses pull subscriptions for workers.

    Parameters:
      project_id: GCP project ID.
      publisher_options: Optional kwargs for PublisherClient (e.g. client_options for emulator).
      subscriber_options: Optional kwargs for SubscriberClient.
      middleware: Optional list of Dramatiq middleware.
    """

    def __init__(
        self,
        project_id: str,
        *,
        publisher_options: Optional[dict[str, Any]] = None,
        subscriber_options: Optional[dict[str, Any]] = None,
        middleware: Optional[list[dramatiq.Middleware]] = None,
    ) -> None:
        super().__init__(middleware=middleware)
        self.project_id = project_id
        self._publisher = pubsub_v1.PublisherClient(**(publisher_options or {}))
        self._subscriber = pubsub_v1.SubscriberClient(**(subscriber_options or {}))
        self.queues: dict[str, str] = {}  # queue_name -> subscription_path

    @property
    def consumer_class(self) -> type[PubSubConsumer]:
        return PubSubConsumer

    def _topic_path(self, queue_name: str) -> str:
        return self._publisher.topic_path(self.project_id, _topic_id(queue_name))

    def _subscription_path(self, queue_name: str) -> str:
        return self._subscriber.subscription_path(
            self.project_id, _subscription_id(queue_name)
        )

    def declare_queue(self, queue_name: str) -> None:
        if queue_name in self.queues:
            return
        self.emit_before("declare_queue", queue_name)
        topic_path = self._topic_path(queue_name)
        subscription_path = self._subscription_path(queue_name)

        try:
            self._publisher.create_topic(request={"name": topic_path})
            self.logger.debug("Created topic %s", topic_path)
        except gcp_exceptions.AlreadyExists:
            pass

        try:
            self._subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                }
            )
            self.logger.debug("Created subscription %s", subscription_path)
        except gcp_exceptions.AlreadyExists:
            pass

        self.queues[queue_name] = subscription_path
        self.emit_after("declare_queue", queue_name)

    def enqueue(self, message: dramatiq.Message, *, delay: Optional[int] = None) -> dramatiq.Message:
        if delay is not None and delay > 0:
            raise NotImplementedError("Delayed messages (eta) are not yet supported")
        queue_name = message.queue_name
        if queue_name not in self.queues:
            raise dramatiq.QueueNotFound(queue_name)
        topic_path = self._topic_path(queue_name)
        self.emit_before("enqueue", message, delay)
        data = message.encode()
        self._publisher.publish(topic_path, data)
        self.logger.debug("Enqueued message %s to %s", message.message_id, queue_name)
        self.emit_after("enqueue", message, delay)
        return message

    def consume(
        self,
        queue_name: str,
        prefetch: int = 1,
        timeout: int = 30000,
    ) -> PubSubConsumer:
        try:
            subscription_path = self.queues[queue_name]
        except KeyError:
            raise dramatiq.QueueNotFound(queue_name) from None
        return self.consumer_class(
            self._subscriber,
            subscription_path,
            prefetch,
            timeout,
        )

    def get_declared_queues(self) -> set[str]:
        return set(self.queues.keys())

    def close(self) -> None:
        self._publisher.transport.close()
        self._subscriber.transport.close()
