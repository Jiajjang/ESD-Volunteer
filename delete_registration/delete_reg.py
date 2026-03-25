from flask import Flask, request, jsonify
import requests, os, json
from datetime import datetime

app = Flask(__name__)

REGISTRATION_URL = os.getenv("REGISTRATION_SERVICE_URL", "http://localhost:5000")

# ─── Cancel registration and promote next ───
@app.route("/cancel-registration", methods=["POST"])
def cancel_registration():
    data = request.get_json()
    volunteer_id = data.get("volunteerID")
    event_id = data.get("eventID")

    # Step 1: Cancel registration in Registration Service
    cancel_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={"volunteerID": volunteer_id, "eventID": event_id, "status": "cancelled"}
    )

    if cancel_resp.status_code != 200:
        return jsonify({"code": cancel_resp.status_code, "message": cancel_resp.text}), cancel_resp.status_code

    # Step 2: (Optional) Promote next volunteer from waitlist here
    # ... implement promotion logic as needed ...

    return jsonify({
        "code": 200,
        "message": f"Volunteer {volunteer_id} cancelled successfully",
        "data": cancel_resp.json().get("data")
    })

if __name__ == "__main__":
    app.run(port=5010, debug=True)