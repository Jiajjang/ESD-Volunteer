from flask import Flask, request, jsonify
import requests, os, json, pika, logging
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from flask_cors import CORS
from flasgger import Swagger
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client
import atexit

# ── Setup ─────────────────────────────────────────────────────────────
load_dotenv()
sg_tz = pytz.timezone("Asia/Singapore")

app = Flask(__name__)
CORS(app)
swagger = Swagger(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────
PROMOTION_TIMEOUT_MINUTES = int(os.getenv("PROMOTION_TIMEOUT_MINUTES", 1))  # 5 min demo

REGISTRATION_URL = os.getenv("REGISTRATION_URL", "http://registration:5000")
EVENT_URL        = os.getenv("EVENT_URL",         "http://event:5001")
VOLUNTEER_URL    = os.getenv("VOLUNTEER_URL",     "http://volunteer:5002")
WAITLIST_URL     = os.getenv("WAITLIST_URL",      "http://waitlist:5003")

# ── RabbitMQ ──────────────────────────────────────────────────────────────────
RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST",  "active-white-bear-01.rmq6.cloudamqp.com")
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER  = os.getenv("RABBITMQ_USER",  "ntxsydfp")
RABBITMQ_PASS  = os.getenv("RABBITMQ_PASS",  "VRMsjW_248ItCPA3gSjNFl51HfiO1Dt9")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "ntxsydfp")
TOPIC_EXCHANGE = os.getenv("TOPIC_EXCHANGE", "G2T7_topic.exchange")

# ── Supabase (for scheduler) ──────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase     = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── RabbitMQ helper ───────────────────────────────────────────────────────────
def publish_message(routing_key: str, message: dict):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters  = pika.ConnectionParameters(
            host=RABBITMQ_HOST, port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST, credentials=credentials,
            heartbeat=600, blocked_connection_timeout=300,
        )
        conn    = pika.BlockingConnection(parameters)
        channel = conn.channel()
        channel.exchange_declare(exchange=TOPIC_EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=TOPIC_EXCHANGE, routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
        conn.close()
        logger.info(f"[AMQP] Published → {routing_key}: {message}")

    except Exception as e:
        logger.error(f"[AMQP] Publish failed for {routing_key}: {e}")
        
EVENT_URL = os.getenv("EVENT_URL", "http://event:5001")
WAITLIST_URL = os.getenv("WAITLIST_URL", "http://waitlist:5003")

# ── RabbitMQ ──────────────────────────────────────────────────────────
# def publish_message(routing_key, message):
#     try:
#         connection = pika.BlockingConnection(
#             pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST"))
#         )
#         channel = connection.channel()
#         channel.exchange_declare(exchange="G2T7_topic.exchange", exchange_type="topic", durable=True)

#         channel.basic_publish(
#             exchange="G2T7_topic.exchange",
#             routing_key=routing_key,
#             body=json.dumps(message),
#         )
#         connection.close()
#     except Exception as e:
#         logger.error(f"[AMQP] {e}")


# ── Event details helper ──────────────────────────────────────────────────────
def get_event_details(event_id: int) -> dict:
    try:
        r = requests.get(f"{EVENT_URL}/event/{event_id}")
        if r.status_code == 200:
            d = r.json().get("data", {})
            return {
                "event_name": d.get("name", ""),
                "start_date": d.get("startDate", d.get("start_date", "")),
                "end_date":   d.get("endDate",   d.get("end_date",   "")),
                "location":   d.get("location",  ""),
            }
    except:
        pass
    return {}

# ── CORE LOGIC ────────────────────────────────────────────────────────

# def auto_timeout(volunteer_id, event_id):
#     logger.info(f"[TIMEOUT] Checking volunteer {volunteer_id}")

#     # check if still pending
#     check = requests.get(f"{REGISTRATION_URL}/registration/{event_id}/{volunteer_id}")
#     if check.status_code == 200:
#         reg = check.json().get("data", {}).get("Registrations", [])
#         if reg and reg[0].get("status") != "pending":
#             logger.info("[TIMEOUT] Already responded → skip")
#             return

#     # cancel
#     requests.put(
#         f"{REGISTRATION_URL}/registration/status",
#         json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "cancelled"},
#     )

#     logger.info(f"[TIMEOUT] Auto-cancelled {volunteer_id}")

#     # loop promotion
#     promote_next(event_id)


# ── Scheduler: auto-cancel expired pending registrations ─────────────────────
def check_expired_pending():
    logger.info("[Scheduler] Checking for expired pending registrations...")
    now = datetime.now(sg_tz).strftime("%Y-%m-%d %H:%M:%S%z")

    try:
        response = supabase.table("registration") \
            .select("*") \
            .eq("status", "pending") \
            .lt("expires_at", now) \
            .execute()

        expired = response.data or []
        logger.info(f"[Scheduler] Found {len(expired)} expired pending registrations")

        for reg in expired:
            volunteer_id = reg["volunteer_id"]
            event_id     = reg["event_id"]
            logger.info(f"[Scheduler] Auto-cancelling volunteer_id={volunteer_id}, event_id={event_id}")
            try:
                resp = requests.put(
                    "http://localhost:5011/cancel-registration/timeout",
                    json={"volunteer_id": volunteer_id, "event_id": event_id}
                )
                logger.info(f"[Scheduler] Timeout result: {resp.status_code} {resp.json()}")
            except Exception as e:
                logger.error(f"[Scheduler] Failed to auto-cancel: {e}")
    except Exception as e:
        logger.error(f"[Scheduler] Error checking expired registrations: {e}")


# Start scheduler — runs every 1 minute
scheduler = BackgroundScheduler()
scheduler.add_job(check_expired_pending, "interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


# ── POST /cancel-registration ─────────────────────────────────────────────────
@app.route("/cancel-registration", methods=["POST"])
def cancel_registration():
    data            = request.get_json()
    volunteer_id    = data.get("volunteer_id")
    event_id        = data.get("event_id")
    registration_id = data.get("registration_id")

    if not volunteer_id or not event_id or not registration_id:
        return jsonify({"code": 400, "message": "volunteer_id, event_id, registration_id required"}), 400

    event_details = get_event_details(event_id)

    cancel_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "cancelled"},
    )
    if cancel_resp.status_code != 200:
        try:
            err_msg = cancel_resp.json().get("message", cancel_resp.text)
        except ValueError:
            err_msg = cancel_resp.text
        return jsonify({"code": cancel_resp.status_code, "message": f"Failed to cancel: {err_msg}"}), cancel_resp.status_code

    cancelled_data = cancel_resp.json().get("data", {})
    email          = cancelled_data.get("email", "")

    publish_message("registration.cancelled", {
        "event_id":   event_id,   "event_name": event_details["event_name"],
        "start_date": event_details["start_date"], "end_date": event_details["end_date"],
        "location":   event_details["location"],   "status": "cancelled", "email": email,
    })

    # ── Get next in waitlist ──────────────────────────────────────
    waitlist_resp        = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")
    next_entry = waitlist_resp.json().get("data") if waitlist_resp.status_code == 200 else None

    promoted_volunteer_id = None
    if next_entry and isinstance(next_entry, dict) and next_entry.get("volunteer_id"):
        promoted_volunteer_id = next_entry.get("volunteer_id")

    # ── No one in waitlist → decrement capacity ───────────────────
    if not promoted_volunteer_id:
        try:
            requests.put(f"{EVENT_URL}/event/{event_id}/capacity", json={"action": "decrement"})
        except Exception as e:
            logger.warning(f"[Decrement] Non-fatal: {e}")
        return jsonify({
            "code": 200, "message": "Cancelled. No one in waitlist. Capacity decremented.",
            "data": {"cancelledVolunteer": cancelled_data, "promotedVolunteerID": None}
        }), 200

    # ── Promote next volunteer → pending (5 mins for testing) ────
    expires_at = (datetime.now(sg_tz) + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S%z")
    promote_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": promoted_volunteer_id, "event_id": event_id, "status": "pending", "expires_at": expires_at},
    )
    if promote_resp.status_code != 200:
        return jsonify({"code": 500, "message": "Cancelled but failed to promote next in waitlist"}), 500

    promoted_data  = promote_resp.json().get("data", {})
    promoted_email = promoted_data.get("email", "")

    publish_message("registration.pending", {
        "event_id":   event_id,   "event_name": event_details["event_name"],
        "start_date": event_details["start_date"], "end_date": event_details["end_date"],
        "location":   event_details["location"],   "status": "pending",
        "email":      promoted_email,              "expires_at": expires_at,
    })

    return jsonify({
        "code": 200,
        "message": f"Volunteer {volunteer_id} cancelled. Volunteer {promoted_volunteer_id} promoted to PENDING.",
        "data": {
            "cancelledVolunteer":  cancelled_data,
            "promotedVolunteerID": promoted_volunteer_id,
            "promotedVolunteer":   promoted_data,
            "expires_at":          expires_at,
        },
    }), 200


# ── PUT /cancel-registration/respond ─────────────────────────────────────────
@app.route("/cancel-registration/respond", methods=["PUT"])
def respond_to_promotion():
    data         = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id     = data.get("event_id")
    status       = data.get("status", "").lower()

    if not volunteer_id or not event_id or status not in ("confirmed", "rejected"):
        return jsonify({"code": 400, "message": "Invalid volunteer_id, event_id, or status"}), 400

    event_details = get_event_details(event_id)

    # ── Confirmed → just update and notify ───────────────────────
    if status == "confirmed":
        update_resp = requests.put(
            f"{REGISTRATION_URL}/registration/status",
            json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "confirmed"}
        )
        if update_resp.status_code != 200:
            return jsonify({"code": 500, "message": "Failed to confirm registration"}), 500

        email = update_resp.json().get("data", {}).get("email", "")
        publish_message("registration.confirmed", {
            "event_id":   event_id,   "event_name": event_details["event_name"],
            "start_date": event_details["start_date"], "end_date": event_details["end_date"],
            "location":   event_details["location"],   "status": "confirmed", "email": email,
        })
        return jsonify({"code": 200, "message": "Registration confirmed"}), 200

    # ── Rejected → cancel, get next in waitlist, promote ─────────
    cancel_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "rejected"} ###
    )
    if cancel_resp.status_code != 200:
        return jsonify({"code": 500, "message": "Failed to cancel registration"}), 500

    cancelled_data = cancel_resp.json().get("data", {})
    email          = cancelled_data.get("email", "")

    publish_message("registration.rejected", { ###
        "event_id":   event_id,   "event_name": event_details["event_name"],
        "start_date": event_details["start_date"], "end_date": event_details["end_date"],
        "location":   event_details["location"],   "status": "rejected", "email": email,
    })

    # ── Get next in waitlist ──────────────────────────────────────
    waitlist_resp         = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")
    next_entry = waitlist_resp.json().get("data") if waitlist_resp.status_code == 200 else None

    promoted_volunteer_id = None
    if next_entry and isinstance(next_entry, dict) and next_entry.get("volunteer_id"):
        promoted_volunteer_id = next_entry.get("volunteer_id")

    # ── No one in waitlist → decrement ───────────────────────────
    if not promoted_volunteer_id:
        try:
            requests.put(f"{EVENT_URL}/event/{event_id}/capacity", json={"action": "decrement"})
        except Exception as e:
            logger.warning(f"[Decrement] Non-fatal: {e}")
        return jsonify({
            "code": 200, "message": "Rejected. No one in waitlist. Capacity decremented.",
            "data": {"cancelledVolunteer": cancelled_data, "promotedVolunteerID": None}
        }), 200

    # ── Promote next → pending (5 mins for testing) ──────────────
    expires_at   = (datetime.now(sg_tz) + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S%z")
    promote_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": promoted_volunteer_id, "event_id": event_id, "status": "pending", "expires_at": expires_at}
    )
    if promote_resp.status_code != 200:
        return jsonify({"code": 500, "message": "Failed to promote next volunteer"}), 500

    promoted_data  = promote_resp.json().get("data", {})
    promoted_email = promoted_data.get("email", "")

    publish_message("registration.pending", {
        "event_id":   event_id,   "event_name": event_details["event_name"],
        "start_date": event_details["start_date"], "end_date": event_details["end_date"],
        "location":   event_details["location"],   "status": "pending",
        "email":      promoted_email,              "expires_at": expires_at,
    })

    return jsonify({
        "code": 200,
        "message": f"Volunteer {volunteer_id} rejected. Volunteer {promoted_volunteer_id} promoted to PENDING.",
        "data": {
            "cancelledVolunteer":  cancelled_data,
            "promotedVolunteerID": promoted_volunteer_id,
            "promotedVolunteer":   promoted_data,
            "expires_at":          expires_at,
        },
    }), 200


# ── PUT /cancel-registration/timeout ─────────────────────────────────────────
@app.route("/cancel-registration/timeout", methods=["PUT"])
def handle_timeout():
    data         = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id     = data.get("event_id")

    if not volunteer_id or not event_id:
        return jsonify({"code": 400, "message": "volunteer_id and event_id required"}), 400
    
    event_details = get_event_details(event_id)

# def promote_next(event_id):
#     logger.info(f"[PROMOTE] Looking for next in waitlist")

#     event_details = get_event_details(event_id)

#     r = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")
#     if r.status_code != 200:
#         logger.warning("[PROMOTE] Waitlist fetch failed")
#         return None

#     entry = r.json().get("data")
#     if not entry:
#         logger.info("[PROMOTE] No one left → decrement capacity")
#         requests.put(f"{EVENT_URL}/event/{event_id}/capacity",
#                      json={"event_id": event_id, "action": "decrement"})
#         return None

#     volunteer_id = entry.get("volunteer_id")

#     expires_at = (datetime.now(sg_tz) + timedelta(minutes=PROMOTION_TIMEOUT_MINUTES))

#     resp = requests.put(
#         f"{REGISTRATION_URL}/registration/status",
#         json={
#             "registration_id": registration_id,
#             "volunteer_id": volunteer_id,
#             "event_id": event_id,
#             "status": "pending",
#             "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S%z"),
#         },
#     )

#     if resp.status_code != 200:
#         logger.error("[PROMOTE] Failed to update registration")
#         return None

#     email = resp.json().get("data", {}).get("email", "")

#     publish_message("registration.pending", {
#         "event_id": event_id,
#         "status": "pending",
#         "email": email,
#     })

#     # schedule timeout
#     scheduler.add_job(
#         auto_timeout,
#         'date',
#         run_date=expires_at,
#         args=[volunteer_id, event_id],
#         id=f"{event_id}_{volunteer_id}",
#         replace_existing=True
#     )

#     logger.info(f"[PROMOTE] {volunteer_id} promoted (timeout in {PROMOTION_TIMEOUT_MINUTES} min)")
#     return volunteer_id

# # ── API ───────────────────────────────────────────────────────────────

# @app.route("/cancel-registration", methods=["POST"])
# def cancel_registration():
#     data = request.get_json()
#     volunteer_id = data.get("volunteer_id")
#     event_id = data.get("event_id")

#     if not volunteer_id or not event_id:
#         return jsonify({"code": 400, "message": "Missing fields"}), 400

#     # cancel
#     resp = requests.put(
#         f"{REGISTRATION_URL}/registration/status",
#         json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "cancelled"},
#     )

    # ── Auto-cancel ───────────────────────────────────────────────
    cancel_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "cancelled"},
#     logger.info(f"[CANCEL] {resp.status_code} {resp.text}")

#     if resp.status_code != 200:
#         return jsonify({"code": 500, "message": "Cancel failed"}), 500

#     # promote next
#     promoted = promote_next(event_id)

#     return jsonify({
#         "code": 200,
#         "message": "Cancelled",
#         "promotedVolunteerID": promoted
#     }), 200


# @app.route("/cancel-registration/respond", methods=["PUT"])
# def respond():
#     data = request.get_json()
#     volunteer_id = data.get("volunteer_id")
#     event_id = data.get("event_id")
#     status = data.get("status")

#     if status not in ["confirmed", "rejected"]:
#         return jsonify({"code": 400, "message": "Invalid status"}), 400

#     # update
#     requests.put(
#         f"{REGISTRATION_URL}/registration/status",
#         json={
#             "registration_id": registration_id,
#             "volunteer_id": volunteer_id,
#             "event_id": event_id,
#             "status": status,
#         },
    )
    if cancel_resp.status_code != 200:
        return jsonify({"code": 500, "message": "Failed to auto-cancel timed-out registration"}), 500

    email = cancel_resp.json().get("data", {}).get("email", "")
    publish_message("registration.cancelled", {
        "event_id":   event_id,   "event_name": event_details["event_name"],
        "start_date": event_details["start_date"], "end_date": event_details["end_date"],
        "location":   event_details["location"],   "status": "cancelled", "email": email,
    })

    # ── Get next in waitlist ──────────────────────────────────────
    waitlist_resp         = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")
    next_entry = waitlist_resp.json().get("data") if waitlist_resp.status_code == 200 else None

    promoted_volunteer_id = None
    if next_entry and isinstance(next_entry, dict) and next_entry.get("volunteer_id"):
        promoted_volunteer_id = next_entry.get("volunteer_id")

    # ── No one in waitlist → decrement ───────────────────────────
    if not promoted_volunteer_id:
        try:
            requests.put(f"{EVENT_URL}/event/{event_id}/capacity", json={"action": "decrement"})
        except Exception as e:
            logger.warning(f"[Timeout Decrement] Non-fatal: {e}")
        return jsonify({"code": 200, "message": "Timed out. No one in waitlist. Capacity decremented."}), 200

    # ── Promote next → pending (5 mins for testing) ──────────────
    expires_at   = (datetime.now(sg_tz) + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S%z")
    promote_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": promoted_volunteer_id, "event_id": event_id, "status": "pending", "expires_at": expires_at}
    )
    if promote_resp.status_code == 200:
        promoted_email = promote_resp.json().get("data", {}).get("email", "")
        publish_message("registration.pending", {
            "event_id":   event_id,   "event_name": event_details["event_name"],
            "start_date": event_details["start_date"], "end_date": event_details["end_date"],
            "location":   event_details["location"],   "status": "pending",
            "email":      promoted_email,              "expires_at": expires_at,
        })

    logger.info(f"[Timeout] Auto-cancelled volunteer_id={volunteer_id}, promoted volunteer_id={promoted_volunteer_id}")
    return jsonify({"code": 200, "message": "Timed out registration cancelled and next volunteer promoted."}), 200


# ── GET /health ───────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"code": 200, "status": "healthy", "service": "cancel-registration-service"}), 200

#     # if rejected → promote next
#     promoted = None
#     if status == "rejected":
#         promoted = promote_next(event_id)

#     return jsonify({
#         "code": 200,
#         "status": status,
#         "promotedVolunteerID": promoted
#     }), 200


# @app.route("/cancel-registration/timeout", methods=["PUT"])
# def timeout():
#     data = request.get_json()
#     volunteer_id = data.get("volunteer_id")
#     event_id = data.get("event_id")
#     registration_id = data.get("registration_id")

#     auto_timeout(volunteer_id, event_id)

#     return jsonify({"code": 200, "message": "Timeout handled"}), 200


# @app.route("/health")
# def health():
#     return jsonify({"status": "ok"}), 200

@app.route("/cancel-waitlist", methods=["POST"])
def cancel_waitlist():
    data         = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id     = data.get("event_id")
    registration_id = data.get("registration_id")

    if not volunteer_id or not event_id or not registration_id:
        return jsonify({"code": 400, "message": "volunteer_id, event_id, registration_id required"}), 400

    # ── Remove from waitlist ──────────────────────────────────────
    wl_resp = requests.delete(f"{WAITLIST_URL}/waitlist/{event_id}/{volunteer_id}")
    if wl_resp.status_code not in (200, 404):  # 404 is ok, might already be removed
        return jsonify({"code": 500, "message": "Failed to remove from waitlist"}), 500

    # ── Cancel registration record ────────────────────────────────
    cancel_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteer_id": volunteer_id, "event_id": event_id, "status": "cancelled"}
    )
    if cancel_resp.status_code != 200:
        return jsonify({"code": 500, "message": "Failed to cancel registration"}), 500

    event_details  = get_event_details(event_id)
    cancelled_data = cancel_resp.json().get("data", {})
    email          = cancelled_data.get("email", "")

    publish_message("registration.cancelled", {
        "event_id":   event_id,
        "event_name": event_details["event_name"],
        "start_date": event_details["start_date"],
        "end_date":   event_details["end_date"],
        "location":   event_details["location"],
        "status":     "cancelled",
        "email":      email,
    })

    return jsonify({
        "code": 200,
        "message": "Successfully removed from waitlist",
        "data": cancelled_data
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=True)