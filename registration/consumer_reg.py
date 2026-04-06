#!/usr/bin/env python3

import os
import json
import time
import pika
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# -----------------------------
# Environment variables
# -----------------------------
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS", "")
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_VHOST = os.environ.get("RABBITMQ_VHOST", "/")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials missing in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# RabbitMQ config
# -----------------------------
FANOUT_EXCHANGE = "G2T7_fanout.exchange"
FANOUT_EXCHANGE_TYPE = "fanout"
FANOUT_QUEUE = "G2T7_fanout.reg.queue"

TOPIC_EXCHANGE = "G2T7_topic.exchange"
TOPIC_EXCHANGE_TYPE = "topic"
TOPIC_ROUTING_KEY = "event.cancelled"


# -----------------------------
# RabbitMQ helpers
# -----------------------------
def get_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=300,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(parameters)


def publish_registrations_purged(channel, payload: dict):
    channel.exchange_declare(
        exchange=TOPIC_EXCHANGE,
        exchange_type=TOPIC_EXCHANGE_TYPE,
        durable=True,
    )

    channel.basic_publish(
        exchange=TOPIC_EXCHANGE,
        routing_key=TOPIC_ROUTING_KEY,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )

    print(f"[AMQP] Published to {TOPIC_EXCHANGE} with routing key '{TOPIC_ROUTING_KEY}'")


# -----------------------------
# Database helpers
# -----------------------------
def get_emails_by_event_id(event_id: int) -> list[str]:
    response = (
        supabase.table("registration")
        .select("email")
        .eq("event_id", event_id)
        .execute()
    )
    rows = response.data or []
    return [row["email"] for row in rows if row.get("email")]


def delete_registrations_by_event_id(event_id: int):
    return (
        supabase.table("registration")
        .delete()
        .eq("event_id", event_id)
        .execute()
    )


# -----------------------------
# Consumer callback
# -----------------------------
def callback(ch, method, properties, body):
    try:
        message = json.loads(body.decode())
        print(f"[AMQP] Received from {FANOUT_QUEUE}: {message}")

        event_id = message.get("event_id")
        event_name = message.get("event_name")
        start_date = message.get("start_date")
        end_date = message.get("end_date")

        if not event_id:
            raise ValueError("event_id is required in consumed message")

        emails = get_emails_by_event_id(event_id)

        outgoing_message = {
            "event_id": event_id,
            "event_name": event_name,
            "start_date": start_date,
            "end_date": end_date,
            "emails": emails,
        }

        # publish first
        publish_registrations_purged(ch, outgoing_message)

        # delete only after publish succeeds
        deleted = delete_registrations_by_event_id(event_id)
        print(f"[DB] Deleted registrations for event_id={event_id}: {deleted.data}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError as e:
        print(f"[AMQP] Invalid JSON: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except Exception as e:
        print(f"[AMQP] Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# -----------------------------
# Consumer loop
# -----------------------------
def start_consumer():
    connection = get_connection()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=FANOUT_EXCHANGE,
        exchange_type=FANOUT_EXCHANGE_TYPE,
        durable=True,
    )

    channel.exchange_declare(
        exchange=TOPIC_EXCHANGE,
        exchange_type=TOPIC_EXCHANGE_TYPE,
        durable=True,
    )

    channel.queue_declare(queue=FANOUT_QUEUE, durable=True)
    channel.queue_bind(
        exchange=FANOUT_EXCHANGE,
        queue=FANOUT_QUEUE,
    )

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue=FANOUT_QUEUE,
        on_message_callback=callback,
        auto_ack=False,
    )

    print(f"[AMQP] Listening on queue '{FANOUT_QUEUE}' from exchange '{FANOUT_EXCHANGE}'")
    channel.start_consuming()


if __name__ == "__main__":
    while True:
        try:
            start_consumer()
        except KeyboardInterrupt:
            print("[AMQP] Consumer stopped by user.")
            break
        except Exception as e:
            print(f"[AMQP] Consumer crashed: {e}")
            print("[AMQP] Reconnecting in 5 seconds...")
            time.sleep(5)