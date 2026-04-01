from flask import Flask, request, jsonify
from flask_cors import CORS
import pika, json, os, requests
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ── Atomic service URLs ──────────────────────────────────────────
REGISTRATION_URL = os.getenv("REGISTRATION_URL",  "http://registration:5000")
EVENT_URL        = os.getenv("EVENT_URL",         "http://event:5001")
VOLUNTEER_URL    = os.getenv("VOLUNTEER_URL",     "http://volunteer:5002")
WAITLIST_URL     = os.getenv("WAITLIST_URL",      "http://waitlist:5003")

RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST", "active-white-bear-01.rmq6.cloudamqp.com")
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "ntxsydfp")
RABBITMQ_USER  = os.getenv("RABBITMQ_USERNAME", "ntxsydfp")
RABBITMQ_PASS  = os.getenv("RABBITMQ_PASSWORD", "VRMsjW_248ItCPA3gSjNFl51HfiO1Dt9")


# ── AMQP helper ──────────────────────────────────────────────────
def publish_notification(routing_key: str, message: dict):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials
            )
        )
        channel = connection.channel()
        channel.exchange_declare(
            exchange="G2T7_topic.exchange",
            exchange_type="topic",
            durable=True
        )
        channel.basic_publish(
            exchange="G2T7_topic.exchange",
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        print(f"[AMQP] Failed to publish: {e}")


# ── Main composite route ─────────────────────────────────────────
@app.route("/register_for_event", methods=["POST"])
def register_for_event():
    data         = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id     = data.get("event_id")

    if not all([volunteer_id, event_id]):
        return jsonify({"code": 400, "message": "volunteer_id and event_id are required."}), 400

    # ── Step 2 & 3: Try to increment event capacity ──────────────
    event_resp = requests.put(
        f"{EVENT_URL}/event/{event_id}/capacity",
        json={"action": "increment"}        # ← matches your event service
    )

    event_full = event_resp.status_code == 400      # 400 = full, 200 = incremented
    
    # event_resp = requests.put(
    #     f"{EVENT_URL}/event/{event_id}/increment"
    # )

    # event_full = event_resp.status_code == 400      # 400 = full, 200 = incremented

    # ── Step 4 & 5: Fetch volunteer particulars ──────────────────
    vol_resp = requests.get(f"{VOLUNTEER_URL}/volunteer/{volunteer_id}")
    if vol_resp.status_code != 200:
        return jsonify({"code": 404, "message": "Volunteer not found."}), 404

    volunteer = vol_resp.json()["data"]
    email     = volunteer["email"]

    # ── Step 6b: Add to waitlist if event is full ────────────────
    if event_full:
        wl_resp = requests.post(
            f"{WAITLIST_URL}/waitlist/{event_id}",    # ← add event_id to URL
            json={"volunteer_id": volunteer_id}        # ← only volunteer_id in body
        )
        if wl_resp.status_code not in (200, 201, 409):  # ← 409 = already in waitlist, still ok
            return jsonify({"code": 500, "message": "Failed to add to waitlist."}), 500
    
    # if event_full:
    #     wl_resp = requests.post(
    #         f"{WAITLIST_URL}/waitlist",
    #         json={
    #             "volunteer_id": volunteer_id
    #         }
    #     )
    #     if wl_resp.status_code not in (200, 201):
    #         return jsonify({"code": 500, "message": "Failed to add to waitlist."}), 500

    # ── Step 6a/8b: Create registration record ───────────────────
    status = "waitlisted" if event_full else "confirmed"
    logger.info(f"status: {status}")

    reg_resp = requests.post(
        f"{REGISTRATION_URL}/registration",
        json={
            "volunteer_id": volunteer_id,
            "email":        email,
            "event_id":     event_id,
            "status":       status
        }
    )
    if reg_resp.status_code not in (200, 201):
        return jsonify({"code": 500, "message": "Failed to create registration."}), 500

    registration_id = reg_resp.json()["data"]["registration_id"]  # ← direct, no second GET needed

    # registration = reg_resp.json()["data"]
    # resp = requests.get(f"{REGISTRATION_URL}/registration/{event_id}/{volunteer_id}")
    # print(f"RESPONSE: {resp}")
    # logger.debug(f"Registration: {resp}")

    # if resp.ok:
    #     data = resp.json()["data"]
    #     logger.debug(f"Registration: {data}")
    #     registration_id = data["Registrations"][0]["registration_id"] if data else None
    # else:
    #     registration_id = None
    # registration_id = registration["registration_id"]

    # ── Fetch event details for response ─────────────────────────
    event_detail_resp = requests.get(f"{EVENT_URL}/event/{event_id}")
    event_data = event_detail_resp.json().get("data", {}) if event_detail_resp.ok else {}
    event_name = event_data.get("event_name")
    location   = event_data.get("location")
    start_date = event_data.get("start_date")
    end_date   = event_data.get("end_date")

    # if event_resp.ok and event_resp.text.strip():
    #     event_details = event_resp.json()
    # else:
    #     logger.warning(f"Event fetch failed: {event_resp.status_code} {event_resp.text[:100]}")
    #     event_details = {}  # Fallback empty
    # logger.debug(f"Event_details: {event_details}")


    # start_date = event_details.get("data", {}).get("start_date")
    # end_date   = event_details.get("data", {}).get("end_date")

    # ── Step 8/10b: Publish AMQP notification ────────────────────
    routing_key = "registration.waitlisted" if event_full else "registration.confirmed"
    publish_notification(routing_key, {
        "registration_id": registration_id,
        "volunteer_id":    volunteer_id,
        "email":           email,
        "event_id":        event_id,
        "event_name":      event_name,
        "location":        location,
        "start_date":      start_date,
        "end_date":        end_date,
        "status":          status
    })

    # ── Step 9a/11b: Return response to UI ───────────────────────
    return jsonify({
        "code": 200,
        "data": {
            "registration_id": registration_id,
            "event_id":        event_id,
            "start_date":      start_date,
            "end_date":        end_date,
            "status":          status
        }
    }), 200


if __name__ == "__main__":
    print("Register for Event composite microservice running...")
    app.run(host="0.0.0.0", port=5010, debug=True)