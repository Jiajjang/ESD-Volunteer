from flask import Flask, request, jsonify
import requests, os, json, pika, logging
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()
sg_tz = pytz.timezone("Asia/Singapore")

app = Flask(__name__)
CORS(app)

from flasgger import Swagger

swagger = Swagger(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Service URLs ──────────────────────────────────────────────────────────────
REGISTRATION_URL = os.getenv("REGISTRATION_URL", "http://registration:5000")
EVENT_URL = os.getenv("EVENT_URL", "http://event:5001")
VOLUNTEER_URL = os.getenv("VOLUNTEER_URL", "http://volunteer:5002")
WAITLIST_URL = os.getenv("WAITLIST_URL", "http://waitlist:5003")

# ── RabbitMQ ──────────────────────────────────────────────────────────────────
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "active-white-bear-01.rmq6.cloudamqp.com")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "ntxsydfp")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "VRMsjW_248ItCPA3gSjNFl51HfiO1Dt9")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "ntxsydfp")
TOPIC_EXCHANGE = os.getenv("TOPIC_EXCHANGE", "G2T7_topic.exchange")


def publish_message(routing_key: str, message: dict):
    """Fire-and-forget publish to G2T7_topic.exchange → Notification Service."""
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )
        conn = pika.BlockingConnection(parameters)
        channel = conn.channel()
        channel.exchange_declare(
            exchange=TOPIC_EXCHANGE, exchange_type="topic", durable=True
        )
        channel.basic_publish(
            exchange=TOPIC_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                content_type="application/json", delivery_mode=2
            ),
        )
        conn.close()
        logger.info(f"[AMQP] Published → {routing_key}: {message}")
    except Exception as e:
        logger.error(f"[AMQP] Publish failed for {routing_key}: {e}")


def get_event_details(event_id: int) -> dict:
    """Fetch event details from Event Service."""
    try:
        resp = requests.get(f"{EVENT_URL}/event/{event_id}")
        if resp.status_code == 200:
            d = resp.json().get("data", {})
            return {
                "event_name": d.get("name", ""),
                "start_date": d.get("startDate", d.get("start_date", "")),
                "end_date": d.get("endDate", d.get("end_date", "")),
                "location": d.get("location", ""),
            }
    except Exception as e:
        logger.warning(f"[Event] Could not fetch event details: {e}")
    return {"event_name": "", "start_date": "", "end_date": "", "location": ""}


# ── POST /cancel-registration ─────────────────────────────────────────────────
@app.route("/cancel-registration", methods=["POST"])
def cancel_registration():
    data = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")
    registration_id = data.get("registration_id")

    if not volunteer_id or not event_id or not registration_id:
        return (
            jsonify(
                {
                    "code": 400,
                    "message": "volunteer_id, event_id, registration_id required",
                }
            ),
            400,
        )

    # ── Fetch event details
    event_details = get_event_details(event_id)

    # ── Cancel registration
    logger.info(f'[Step 2] Deleting registration_id={registration_id}')
    cancel_resp = requests.delete(
    f"{REGISTRATION_URL}/registration",
    json={
        "volunteer_id": volunteer_id,
        "event_id":     event_id
    }
)
    if cancel_resp.status_code != 200:
        return jsonify({"code": cancel_resp.status_code, "message": f"Failed to cancel registration: {cancel_resp.text}"}), cancel_resp.status_code
    
    email = ""
    cancelled_data = {"volunteerID": volunteer_id, "eventID": event_id}

    # cancelled_data = cancel_resp.json().get("data", {})
    # email = cancelled_data.get("email", "")

    # ── Notify cancellation
    publish_message(
        "registration.cancelled",
        {
            "event_id": event_id,
            "event_name": event_details["event_name"],
            "start_date": event_details["start_date"],
            "end_date": event_details["end_date"],
            "location": event_details["location"],
            "status": "cancelled",
            "email": email,
        },
    )

    # ── Get next waitlisted volunteer
    waitlist_resp = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")
    next_entry = (
        waitlist_resp.json().get("data") if waitlist_resp.status_code == 200 else None
    )
    promoted_volunteer_id = next_entry.get("volunteer_id") if next_entry else None

    # ── If no one in waitlist → decrement capacity
    if not promoted_volunteer_id:
        logger.info(
            f"[Step 7L] Queue empty — decrementing capacity for event_id={event_id}"
        )
        capacity_data = {}
        try:
            capacity_resp = requests.put(
                f"{EVENT_URL}/event/capacity",
                json={"event_id": event_id, "action": "decrement"},
            )
            capacity_data = capacity_resp.json().get("data", {})
        except Exception as e:
            logger.warning(f"[Step 7L] Event Service error (non-fatal): {e}")

        return (
            jsonify(
                {
                    "code": 200,
                    "message": "Cancelled. No one in waitlist. Capacity decremented.",
                    "data": {
                        "cancelledVolunteer": cancelled_data,
                        "promotedVolunteerID": None,
                        "capacity": capacity_data,
                    },
                }
            ),
            200,
        )

    # ── Promote waitlisted volunteer → pending
    expires_at = (datetime.now(sg_tz) + timedelta(hours=24)).strftime(
        "%Y-%m-%d %H:%M:%S%z"
    )
    logger.info(
        f"[Step 7] Promoting volunteer_id={promoted_volunteer_id} to PENDING until {expires_at}"
    )
    promote_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={
            "volunteer_id": promoted_volunteer_id,
            "event_id": event_id,
            "status": "pending",
            "expires_at": expires_at,
        },
    )

    if promote_resp.status_code != 200:
        return (
            jsonify(
                {
                    "code": 500,
                    "message": "Cancelled volunteer but failed to promote next in waitlist",
                    "data": {
                        "cancelledVolunteer": cancelled_data,
                        "waitlistEntry": next_entry,
                    },
                }
            ),
            500,
        )

    promoted_data = promote_resp.json().get("data", {})
    promoted_email = promoted_data.get("email", "")

    # ── Notify promotion
    publish_message(
        "registration.pending",
        {
            "event_id": event_id,
            "event_name": event_details["event_name"],
            "start_date": event_details["start_date"],
            "end_date": event_details["end_date"],
            "location": event_details["location"],
            "status": "pending",
            "email": promoted_email,
            "expires_at": expires_at,
        },
    )

    return (
        jsonify(
            {
                "code": 200,
                "message": f"Volunteer {volunteer_id} cancelled. Volunteer {promoted_volunteer_id} promoted to PENDING.",
                "data": {
                    "cancelledVolunteer": cancelled_data,
                    "promotedVolunteerID": promoted_volunteer_id,
                    "promotedVolunteer": promoted_data,
                    "expires_at": expires_at,
                },
            }
        ),
        200,
    )


# ── PUT /cancel-registration/respond ─────────────────────────────────────────
@app.route("/cancel-registration/respond", methods=["PUT"])
def respond_to_promotion():
    """Respond to a waitlist promotion
    ---
    tags:
      - Cancel Registration
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - volunteer_id
            - event_id
            - status
          properties:
            volunteer_id:
              type: integer
              example: 99
            event_id:
              type: integer
              example: 3
            status:
              type: string
              enum: [confirmed, rejected]
              example: confirmed
    responses:
      200:
        description: Registration status updated
      400:
        description: Invalid fields
      500:
        description: Failed to update status
    """

    data = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")
    status = data.get("status", "").lower()

    if not volunteer_id or not event_id or status not in ("confirmed", "rejected"):
        return (
            jsonify(
                {"code": 400, "message": "Invalid volunteer_id, event_id, or status"}
            ),
            400,
        )

    event_details = get_event_details(event_id)

    update_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": volunteer_id, "event_id": event_id, "status": status},
    )

    if update_resp.status_code != 200:
        return (
            jsonify({"code": 500, "message": "Failed to update registration status"}),
            500,
        )

    email = update_resp.json().get("data", {}).get("email", "")

    publish_message(
        f"registration.{status}",
        {
            "event_id": event_id,
            "event_name": event_details["event_name"],
            "start_date": event_details["start_date"],
            "end_date": event_details["end_date"],
            "location": event_details["location"],
            "status": status,
            "email": email,
        },
    )

    return jsonify({"code": 200, "message": f"Registration {status}"}), 200


### TO FIX!!! ###
""" THIS PART IM REALLY NOT SURE, I KEEP GETTING AN ERROR WHEN THIS PART OF THE TEST SCRIPT RUNS BUT NGL IDK IF I'M EVEN DOING IT RIGHT """


# ── PUT /cancel-registration/timeout ─────────────────────────────────────────
@app.route("/cancel-registration/timeout", methods=["PUT"])
def handle_timeout():
    """Auto-cancel a pending registration after timeout
    ---
    tags:
      - Cancel Registration
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - volunteer_id
            - event_id
          properties:
            volunteer_id:
              type: integer
              example: 99
            event_id:
              type: integer
              example: 3
    responses:
      200:
        description: Timed out registration cancelled
      400:
        description: Missing required fields
      500:
        description: Failed to auto-cancel
    """

    data = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")

    if not volunteer_id or not event_id:
        return (
            jsonify({"code": 400, "message": "volunteer_id and event_id required"}),
            400,
        )

    event_details = get_event_details(event_id)

    # Auto-cancel
    check = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={
            "volunteer_id": volunteer_id,
            "event_id": event_id,
            "status": "cancelled",
        },
    )

    if check.status_code != 200:
        return (
            jsonify(
                {"code": 500, "message": "Failed to auto-cancel timed-out registration"}
            ),
            500,
        )

    email = check.json().get("data", {}).get("email", "")

    publish_message(
        "registration.cancelled",
        {
            "event_id": event_id,
            "event_name": event_details["event_name"],
            "start_date": event_details["start_date"],
            "end_date": event_details["end_date"],
            "location": event_details["location"],
            "status": "cancelled",
            "email": email,
        },
    )

    logger.info(
        f"[Timeout] Auto-cancelled volunteer_id={volunteer_id} for event_id={event_id}"
    )
    return jsonify({"code": 200, "message": "Timed out registration cancelled"}), 200


# ── Health Check
@app.route("/health", methods=["GET"])
def health():
    """Health check
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy
    """
    return (
        jsonify(
            {"code": 200, "status": "healthy", "service": "cancel-registration-service"}
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=True)
