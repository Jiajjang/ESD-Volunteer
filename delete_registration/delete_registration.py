from flask import Flask, request, jsonify
import requests, os, json, pika, logging
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

# ── Setup ─────────────────────────────────────────────────────────────
load_dotenv()
sg_tz = pytz.timezone("Asia/Singapore")

app = Flask(__name__)
CORS(app)

scheduler = BackgroundScheduler()
scheduler.start()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────
PROMOTION_TIMEOUT_MINUTES = int(os.getenv("PROMOTION_TIMEOUT_MINUTES", 1))  # 5 min demo

REGISTRATION_URL = os.getenv("REGISTRATION_URL", "http://registration:5000")
EVENT_URL = os.getenv("EVENT_URL", "http://event:5001")
WAITLIST_URL = os.getenv("WAITLIST_URL", "http://waitlist:5003")

# ── RabbitMQ ──────────────────────────────────────────────────────────
def publish_message(routing_key, message):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST"))
        )
        channel = connection.channel()
        channel.exchange_declare(exchange="G2T7_topic.exchange", exchange_type="topic", durable=True)

        channel.basic_publish(
            exchange="G2T7_topic.exchange",
            routing_key=routing_key,
            body=json.dumps(message),
        )
        connection.close()
    except Exception as e:
        logger.error(f"[AMQP] {e}")

# ── Helpers ───────────────────────────────────────────────────────────
def get_event_details(event_id):
    try:
        r = requests.get(f"{EVENT_URL}/event/{event_id}")
        if r.status_code == 200:
            d = r.json().get("data", {})
            return {
                "event_name": d.get("name", ""),
                "start_date": d.get("startDate", ""),
                "end_date": d.get("endDate", ""),
                "location": d.get("location", ""),
            }
    except:
        pass
    return {}

# ── CORE LOGIC ────────────────────────────────────────────────────────

def auto_timeout(volunteer_id, event_id):
    logger.info(f"[TIMEOUT] Checking volunteer {volunteer_id}")

    # check if still pending
    check = requests.get(f"{REGISTRATION_URL}/registration/{event_id}/{volunteer_id}")
    if check.status_code == 200:
        reg = check.json().get("data", {}).get("Registrations", [])
        if reg and reg[0].get("status") != "pending":
            logger.info("[TIMEOUT] Already responded → skip")
            return

    # cancel
    requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "cancelled"},
    )

    logger.info(f"[TIMEOUT] Auto-cancelled {volunteer_id}")

    # loop promotion
    promote_next(event_id)


def promote_next(event_id):
    logger.info(f"[PROMOTE] Looking for next in waitlist")

    event_details = get_event_details(event_id)

    r = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")
    if r.status_code != 200:
        logger.warning("[PROMOTE] Waitlist fetch failed")
        return None

    entry = r.json().get("data")
    if not entry:
        logger.info("[PROMOTE] No one left → decrement capacity")
        requests.put(f"{EVENT_URL}/event/{event_id}/capacity",
                     json={"event_id": event_id, "action": "decrement"})
        return None

    volunteer_id = entry.get("volunteer_id")

    expires_at = (datetime.now(sg_tz) + timedelta(minutes=PROMOTION_TIMEOUT_MINUTES))

    resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={
            "registration_id": registration_id,
            "volunteer_id": volunteer_id,
            "event_id": event_id,
            "status": "pending",
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S%z"),
        },
    )

    if resp.status_code != 200:
        logger.error("[PROMOTE] Failed to update registration")
        return None

    email = resp.json().get("data", {}).get("email", "")

    publish_message("registration.pending", {
        "event_id": event_id,
        "status": "pending",
        "email": email,
    })

    # schedule timeout
    scheduler.add_job(
        auto_timeout,
        'date',
        run_date=expires_at,
        args=[volunteer_id, event_id],
        id=f"{event_id}_{volunteer_id}",
        replace_existing=True
    )

    logger.info(f"[PROMOTE] {volunteer_id} promoted (timeout in {PROMOTION_TIMEOUT_MINUTES} min)")
    return volunteer_id

# ── API ───────────────────────────────────────────────────────────────

@app.route("/cancel-registration", methods=["POST"])
def cancel_registration():
    data = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")

    if not volunteer_id or not event_id:
        return jsonify({"code": 400, "message": "Missing fields"}), 400

    # cancel
    resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "cancelled"},
    )

    logger.info(f"[CANCEL] {resp.status_code} {resp.text}")

    if resp.status_code != 200:
        return jsonify({"code": 500, "message": "Cancel failed"}), 500

    # promote next
    promoted = promote_next(event_id)

    return jsonify({
        "code": 200,
        "message": "Cancelled",
        "promotedVolunteerID": promoted
    }), 200


@app.route("/cancel-registration/respond", methods=["PUT"])
def respond():
    data = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")
    status = data.get("status")

    if status not in ["confirmed", "rejected"]:
        return jsonify({"code": 400, "message": "Invalid status"}), 400

    # update
    requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={
            "registration_id": registration_id,
            "volunteer_id": volunteer_id,
            "event_id": event_id,
            "status": status,
        },
    )

    # if rejected → promote next
    promoted = None
    if status == "rejected":
        promoted = promote_next(event_id)

    return jsonify({
        "code": 200,
        "status": status,
        "promotedVolunteerID": promoted
    }), 200


@app.route("/cancel-registration/timeout", methods=["PUT"])
def timeout():
    data = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")
    registration_id = data.get("registration_id")

    auto_timeout(volunteer_id, event_id)

    return jsonify({"code": 200, "message": "Timeout handled"}), 200


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=True)