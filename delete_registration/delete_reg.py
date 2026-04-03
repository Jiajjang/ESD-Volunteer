from flask import Flask, request, jsonify
import requests, os
from flask_cors import CORS
from datetime import datetime, timedelta
import pytz


# Timezone
sg_tz = pytz.timezone('Asia/Singapore')

app = Flask(__name__)
CORS(app)

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
        
    # Step 0: Check Registration Status
    status_resp = requests.get(f"{REGISTRATION_URL}/registration/{event_id}/{volunteer_id}")
    status_data = status_resp.json()
    
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
    # Step 1.5: DECREMENT IF REGISTRATION TO BE DELETED IS NOT A WAITLISTED REGISTRATION
    registrations = status_data.get("data", {}).get("Registrations", [])
    decrement_success = True

    if registrations:
        reg_status = registrations[0].get("status") 
        print(f"DEBUG: Registration status is '{reg_status}'")
        
        if reg_status != 'waitlisted':
            decrement_resp = requests.put(
                f"{EVENT_URL}/event/{event_id}/capacity",
                json={"action": "decrement"}
            )
            print(f"DEBUG: Decrement response: {decrement_resp.status_code}")
            decrement_success = decrement_resp.status_code == 200
        else:
            print("DEBUG: Waitlisted registration, skipping decrement")
    else:
        print("DEBUG: No registration found, skipping decrement")

    if cancel_resp.status_code != 200 or not decrement_success:
        return jsonify({
            "code": 500,
            "message": f"Failed to cancel registration: {cancel_resp.text}"
        }), 500

    cancelled_data = cancel_resp.json().get("data")

    # Step 2: Get next waitlisted volunteer
    waitlist_resp = requests.get(f"{WAITLIST_URL}/waitlist/{event_id}/next")
    if waitlist_resp.status_code != 200:
        return jsonify({
            "code": 500,
            "message": "Cancelled volunteer, but failed to retrieve next waitlisted volunteer",
            "data": {
                "cancelledVolunteer": cancelled_data
            }
        }), 500

    waitlist_json = waitlist_resp.json()
    next_entry = waitlist_json.get("data")
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
    if not next_entry:
        return jsonify({
            "code": 200,
            "message": f"Volunteer {volunteer_id} cancelled successfully. No waitlisted volunteer to promote.",
            "data": {
                "cancelledVolunteer": cancelled_data,
                "promotedVolunteerID": None
            }
        }), 200
    
    promoted_volunteer_id = next_entry.get("volunteer_id")
    print("DEBUG promoted_volunteer_id:", promoted_volunteer_id)

    promote_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={
            "volunteer_id": promoted_volunteer_id,
            "event_id": event_id,
            "status": "pending",
            "expires_at": (datetime.now(sg_tz) + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        }
    )

    print("DEBUG promote status:", promote_resp.status_code)
    print("DEBUG promote body:", promote_resp.text)

    if promote_resp.status_code == 200:
        promoted_data = promote_resp.json().get("data")

        increment_resp = requests.put(
            f"{EVENT_URL}/event/{event_id}/capacity",
            json={"action": "increment"}
        )

        print("DEBUG increment status:", increment_resp.status_code)
        print("DEBUG increment body:", increment_resp.text)

        if not increment_resp.ok:
            return jsonify({
                "code": 500,
                "message": "Promoted volunteer, but failed to increment event capacity",
                "data": {
                    "cancelledVolunteer": cancelled_data,
                    "promotedVolunteer": promoted_data
                }
            }), 500
    else:
        return jsonify({
            "code": 500,
            "message": "Cancelled volunteer, but failed to promote next waitlisted volunteer",
            "data": {
                "cancelledVolunteer": cancelled_data,
                "waitlistEntry": next_entry,
                "promoteError": promote_resp.text
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