from flask import Flask, request, jsonify
from flask_cors import CORS
import pika, json, os, requests
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

# ── Atomic service URLs ──────────────────────────────────────────
REGISTRATION_URL = os.getenv("REGISTRATION_URL",  "http://registration:5000")
EVENT_URL        = os.getenv("EVENT_URL",         "http://event:5001")
VOLUNTEER_URL    = os.getenv("VOLUNTEER_URL",     "http://volunteer:5002")
WAITLIST_URL     = os.getenv("WAITLIST_URL",      "http://waitlist:5003")
RABBITMQ_HOST    = os.getenv("RABBITMQ_HOST",     "rabbitmq")


# ── AMQP helper ──────────────────────────────────────────────────
def publish_notification(routing_key: str, message: dict):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.exchange_declare(
            exchange="notification",
            exchange_type="topic",
            durable=True
        )
        channel.basic_publish(
            exchange="notification",
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
        f"{EVENT_URL}/event/{event_id}/increment"
    )

    event_full = event_resp.status_code == 400      # 400 = full, 200 = incremented

    # ── Step 4 & 5: Fetch volunteer particulars ──────────────────
    vol_resp = requests.get(f"{VOLUNTEER_URL}/volunteer/{volunteer_id}")
    if vol_resp.status_code != 200:
        return jsonify({"code": 404, "message": "Volunteer not found."}), 404

    volunteer = vol_resp.json()["data"]
    email     = volunteer["email"]

    # ── Step 6b: Add to waitlist if event is full ────────────────
    if event_full:
        wl_resp = requests.post(
            f"{WAITLIST_URL}/waitlist",
            json={
                "volunteer_id": volunteer_id
            }
        )
        if wl_resp.status_code not in (200, 201):
            return jsonify({"code": 500, "message": "Failed to add to waitlist."}), 500

    # ── Step 6a/8b: Create registration record ───────────────────
    status = "waitlisted" if event_full else "confirmed"

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

    registration    = reg_resp.json()["data"]
    registration_id = registration["registration_id"]

    # ── Fetch event details for response ─────────────────────────
    event_details = event_resp.json() if not event_full else requests.get(
        f"{EVENT_URL}/event/{event_id}"
    ).json()

    start_date = event_details.get("data", {}).get("start_date")
    end_date   = event_details.get("data", {}).get("end_date")

    # ── Step 8/10b: Publish AMQP notification ────────────────────
    routing_key = "registration.waitlisted" if event_full else "registration.confirmed"
    publish_notification(routing_key, {
        "registration_id": registration_id,
        "volunteer_id":    volunteer_id,
        "email":           email,
        "event_id":        event_id,
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