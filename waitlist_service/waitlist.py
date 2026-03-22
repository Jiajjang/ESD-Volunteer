from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os, json, threading, pika, logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Database ──────────────────────────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///waitlist.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── RabbitMQ config ───────────────────────────────────────────────────────────
RABBITMQ_HOST   = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT   = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER   = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS   = os.environ.get('RABBITMQ_PASS', 'guest')
RABBITMQ_VHOST  = os.environ.get('RABBITMQ_VHOST', '/')
FANOUT_EXCHANGE = os.environ.get('FANOUT_EXCHANGE', 'G2T7_fanout.exchange')

# ── Model — 4 columns only, no status ────────────────────────────────────────
# Status (PENDING/CONFIRMED/REJECTED/CANCELLED) lives in Registration Service.
# Waitlist only tracks who is in the queue and in what order.
class WaitlistEntry(db.Model):
    __tablename__ = 'waitlist'

    waitlistID  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    volunteerID = db.Column(db.Integer, nullable=False)
    eventID     = db.Column(db.Integer, nullable=False, index=True)
    joinedAt    = db.Column(db.DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('eventID', 'volunteerID', name='uq_event_volunteer'),
    )

    def to_dict(self):
        return {
            'waitlistID':  self.waitlistID,
            'volunteerID': self.volunteerID,
            'eventID':     self.eventID,
            'joinedAt':    self.joinedAt.isoformat() if self.joinedAt else None,
        }

with app.app_context():
    db.create_all()

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


# ── POST /waitlist/<eventID> ──────────────────────────────────────────────────
# SCENARIO 1 — Adds volunteer to the back of the queue.
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/waitlist/<int:event_id>', methods=['POST'])
def add_to_waitlist(event_id):
    """
    Body:    { "volunteerID": 201 }
    Returns: 201 with new entry | 409 if already in queue | 400 if missing field
    """
    data = request.get_json()
    if not data or not data.get('volunteerID'):
        return jsonify({'error': 'volunteerID is required'}), 400

    volunteer_id = data['volunteerID']

    existing = WaitlistEntry.query.filter_by(eventID=event_id, volunteerID=volunteer_id).first()
    if existing:
        return jsonify({
            'error': 'Volunteer is already in the waitlist queue for this event',
            'waitlist': existing.to_dict()
        }), 409

    entry = WaitlistEntry(volunteerID=volunteer_id, eventID=event_id, joinedAt=datetime.now())
    db.session.add(entry)
    db.session.commit()

    logger.info(f'[Waitlist] Added volunteerID={volunteer_id} to queue for eventID={event_id}')
    return jsonify({'message': 'Volunteer added to waitlist', 'waitlist': entry.to_dict()}), 201


# ── GET /waitlist/<eventID>/next ──────────────────────────────────────────────
# SCENARIO 2 — Returns the first person in the queue (oldest joinedAt) AND removes them
# from the queue in the same operation — an atomic pop.
#
# Registration Service then takes over: creates a PENDING registration for
# that volunteer, starts the 24h response timer, sends notification, etc.
# Waitlist Service is done — it doesn't care what happens next.
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/waitlist/<int:event_id>/next', methods=['GET'])
def get_next_volunteer(event_id):
    """
    Returns: { volunteerID, waitlistID, eventID, joinedAt }
         or: { volunteerID: null } if queue is empty
    """
    entry = (
        WaitlistEntry.query
        .filter_by(eventID=event_id)
        .order_by(WaitlistEntry.joinedAt.asc())
        .first()
    )

    if not entry:
        logger.info(f'[Waitlist] Queue is empty for eventID={event_id}')
        return jsonify({'volunteerID': None}), 200

    result = entry.to_dict()          # capture before deleting
    db.session.delete(entry)
    db.session.commit()

    logger.info(f'[Waitlist] Popped volunteerID={result["volunteerID"]} from queue for eventID={event_id}')
    return jsonify(result), 200


# ── GET /waitlist/<eventID> ───────────────────────────────────────────────────
# Utility — view the full queue in order (organiser UI / debugging)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/waitlist/<int:event_id>', methods=['GET'])
def get_waitlist(event_id):
    entries = (
        WaitlistEntry.query
        .filter_by(eventID=event_id)
        .order_by(WaitlistEntry.joinedAt.asc())
        .all()
    )
    return jsonify({
        'eventID':  event_id,
        'count':    len(entries),
        'waitlist': [e.to_dict() for e in entries]
    }), 200


# ── GET /health ───────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'waitlist-service'}), 200


# ── AMQP Fanout Consumer — SCENARIO 3 ────────────────────────────────────────
# Event Service publishes to G2T7_fanout.exchange when organiser cancels event.
# Waitlist Service receives this and deletes ALL queue entries for that event.
# This is pure choreography — no HTTP call needed, no orchestrator involved.
# ─────────────────────────────────────────────────────────────────────────────
def handle_event_cancelled(ch, method, properties, body):
    try:
        message  = json.loads(body)
        event_id = message.get('data', {}).get('eventID') or message.get('eventID')

        if not event_id:
            logger.warning('[AMQP] event.cancelled received with no eventID — ignoring')
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.info(f'[AMQP] Received event.cancelled for eventID={event_id}')

        with app.app_context():
            deleted = WaitlistEntry.query.filter_by(eventID=event_id).delete()
            db.session.commit()

        logger.info(f'[AMQP] Cleared {deleted} queue entries for eventID={event_id}')
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
            result     = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
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
