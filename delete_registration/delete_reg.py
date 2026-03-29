from flask import Flask, request, jsonify
import requests, os
from datetime import datetime, timedelta
import pytz

# Timezone
sg_tz = pytz.timezone('Asia/Singapore')

app = Flask(__name__)

REGISTRATION_URL = os.getenv("REGISTRATION_SERVICE_URL", "http://registration:5000")
WAITLIST_URL = os.getenv("WAITLIST_SERVICE_URL", "http://waitlist:5003")
EVENT_URL = os.getenv("EVENT_SERVICE_URL", "http://event:5001")

@app.route("/cancel-registration", methods=["POST"])
def cancel_registration():
    data = request.get_json()
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")

    if not volunteer_id or not event_id:
        return jsonify({
            "code": 400,
            "message": "volunteer_id and event_id are required"
        }), 400

    # Step 1: Cancel the confirmed registration (STEP 2. STEP 3,4 MISSING)
    cancel_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={
            "volunteer_id": volunteer_id,
            "event_id": event_id,
            "status": "cancelled",
            "expires_at": None
        }
    )

    if cancel_resp.status_code != 200: #WHAT TO DO AFTER THIS?
        return jsonify({
            "code": cancel_resp.status_code,
            "message": f"Failed to cancel registration: {cancel_resp.text}"
        }), cancel_resp.status_code

    cancelled_data = cancel_resp.json().get("data")

    # Step 2: Get next waitlisted volunteer
    waitlist_resp = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")

    if waitlist_resp.status_code != 200: #WHAT TO DO AFTER THIS?
        return jsonify({
            "code": 500,
            "message": "Cancelled volunteer, but failed to retrieve next waitlisted volunteer",
            "data": {
                "cancelledVolunteer": cancelled_data
            }
        }), 500

    waitlist_json = waitlist_resp.json()

    promoted_data = None
    promoted_volunteer_id = None

    # If queue is empty
    if waitlist_json.get("volunteer_id") is None and "data" not in waitlist_json:
        return jsonify({
            "code": 200,
            "message": f"Volunteer {volunteer_id} cancelled successfully. No waitlisted volunteer to promote.",
            "data": {
                "cancelledVolunteer": cancelled_data,
                "promotedVolunteerID": None
            }
        }), 200

    # If there is someone in waitlist
    next_entry = waitlist_json.get("data")
    if next_entry:
        promoted_volunteer_id = next_entry.get("volunteer_id")

        promote_resp = requests.put(
            f"{REGISTRATION_URL}/registration/status",
            json={
                "volunteer_id": promoted_volunteer_id,
                "event_id": event_id,
                "status": "pending",
                "expires_at" : (datetime.now(sg_tz) + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S') #need double check 
            }
        )

        if promote_resp.status_code == 200:
            promoted_data = promote_resp.json().get("data")
        else:
            return jsonify({
                "code": 500,
                "message": "Cancelled volunteer, but failed to promote next waitlisted volunteer",
                "data": {
                    "cancelledVolunteer": cancelled_data,
                    "waitlistEntry": next_entry
                }
            }), 500

    return jsonify({
        "code": 200,
        "message": f"Volunteer {volunteer_id} cancelled successfully",
        "data": {
            "cancelledVolunteer": cancelled_data,
            "promotedVolunteerID": promoted_volunteer_id,
            "promotedVolunteer": promoted_data
        }
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=False)