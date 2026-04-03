from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os, json, threading, pika, logging

from datetime import datetime
import pytz
sg_tz = pytz.timezone('Asia/Singapore')

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Supabase ──────────────────────────────────────────────────────────────────
supabase = create_client(
    os.environ.get('SUPABASE_URL'),
    os.environ.get('SUPABASE_KEY')
)

# ── RabbitMQ config ───────────────────────────────────────────────────────────
RABBITMQ_HOST   = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT   = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER   = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS   = os.environ.get('RABBITMQ_PASS', 'guest')
RABBITMQ_VHOST  = os.environ.get('RABBITMQ_VHOST', '/')
FANOUT_EXCHANGE = os.environ.get('FANOUT_EXCHANGE', 'G2T7_fanout.exchange')

# ── RabbitMQ helper ───────────────────────────────────────────────────────────
def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters  = pika.ConnectionParameters(
        host=RABBITMQ_HOST, port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600, blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)


# ── POST /waitlist/<event_id> ─────────────────────────────────────────────────
# SCENARIO 1 — Called by Register for Event composite when event is full.
# Adds volunteer to the back of the queue.
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/waitlist/<int:event_id>', methods=['POST'])
def add_to_waitlist(event_id):
    """
    Body:    { "volunteer_id": 201 }
    Returns: 201 with new entry | 409 if already in queue | 400 if missing field
    """
    data = request.get_json()
    if not data or not data.get('volunteer_id'):
        return jsonify({'code': 400, 'message': 'volunteer_id is required'}), 400

    volunteer_id = data['volunteer_id']

    # Check for duplicate
    existing = supabase.table('waitlist') \
        .select('*') \
        .eq('event_id', event_id) \
        .eq('volunteer_id', volunteer_id) \
        .execute()

    if existing.data:
        return jsonify({
            'code': 409,
            'message': 'Volunteer is already in the waitlist queue for this event',
            'data': existing.data[0]
        }), 409

    # Insert new entry — joined_at defaults to now() in Supabase
    response = supabase.table('waitlist') \
        .insert({
            'event_id': event_id, 
            'volunteer_id': volunteer_id,
            'joined_at': datetime.now(sg_tz).strftime('%Y-%m-%d %H:%M:%S')
            }) \
        .execute()

    if response.data:
        logger.info(f'[Waitlist] Added volunteer_id={volunteer_id} to queue for event_id={event_id}')
        return jsonify({'code': 201, 'data': response.data[0]}), 201

    return jsonify({'code': 500, 'message': 'Error adding to waitlist'}), 500


# ── GET /waitlist/<event_id>/next ─────────────────────────────────────────────
# SCENARIO 2 — Called by Cancel Registration composite when a slot opens.
# Returns AND removes the first person in the queue (oldest joined_at).
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/waitlist/<int:event_id>/next', methods=['GET'])
def get_next_volunteer(event_id):
    """
    Returns: { waitlist_id, volunteer_id, event_id, joined_at }
         or: { volunteer_id: null } if queue is empty
    """
    # Get the oldest entry (first in queue)
    response = supabase.table('waitlist') \
        .select('*') \
        .eq('event_id', event_id) \
        .order('joined_at', desc=False) \
        .limit(1) \
        .execute()

    if not response.data:
        logger.info(f'[Waitlist] Queue is empty for event_id={event_id}')
        return jsonify({'code': 200, 'volunteer_id': None}), 200

    entry       = response.data[0]
    waitlist_id = entry['waitlist_id']

    # Delete the row
    supabase.table('waitlist') \
        .delete() \
        .eq('waitlist_id', waitlist_id) \
        .execute()

    logger.info(f'[Waitlist] Popped volunteer_id={entry["volunteer_id"]} from queue for event_id={event_id}')
    return jsonify({'code': 200, 'data': entry}), 200


# ── GET /waitlist/<event_id> ──────────────────────────────────────────────────
# Utility — view the full queue in order (organiser UI / debugging)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/waitlist/<int:event_id>', methods=['GET'])
def get_waitlist(event_id):
    response = supabase.table('waitlist') \
        .select('*') \
        .eq('event_id', event_id) \
        .order('joined_at', desc=False) \
        .execute()

    return jsonify({
        'code':     200,
        'event_id': event_id,
        'count':    len(response.data),
        'data':     response.data
    }), 200


# ── GET /health ───────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'code': 200, 'status': 'healthy', 'service': 'waitlist-service'}), 200


# ── AMQP Fanout Consumer — SCENARIO 3 ────────────────────────────────────────
# Listens on G2T7_fanout.exchange. When Event Service cancels an event,
# deletes ALL waitlist entries for that event.
# ─────────────────────────────────────────────────────────────────────────────
def handle_event_cancelled(ch, method, properties, body):
    try:
        message  = json.loads(body)
        event_id = message.get('data', {}).get('event_id') or message.get('event_id')

        if not event_id:
            logger.warning('[AMQP] event.cancelled received with no event_id — ignoring')
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.info(f'[AMQP] Received event.cancelled for event_id={event_id}')

        response = supabase.table('waitlist') \
            .delete() \
            .eq('event_id', event_id) \
            .execute()

        logger.info(f'[AMQP] Cleared waitlist for event_id={event_id}')
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f'[AMQP] Error handling event.cancelled: {e}')
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_amqp_consumer():
    while True:
        try:
            conn    = get_rabbitmq_connection()
            channel = conn.channel()
            channel.exchange_declare(exchange=FANOUT_EXCHANGE, exchange_type='fanout', durable=True)
            queue_name     = 'G2T7_fanout.waitlist.queue'
            channel.queue_declare(queue=queue_name, durable=True)
            channel.queue_bind(exchange=FANOUT_EXCHANGE, queue=queue_name)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=handle_event_cancelled)
            logger.info(f'[AMQP] Listening on fanout exchange "{FANOUT_EXCHANGE}"')
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f'[AMQP] Connection lost, retrying in 5s: {e}')
            import time; time.sleep(5)
        except Exception as e:
            logger.error(f'[AMQP] Consumer error, retrying in 5s: {e}')
            import time; time.sleep(5)


if __name__ == '__main__':
    threading.Thread(target=start_amqp_consumer, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5003)), debug=True)