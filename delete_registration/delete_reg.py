from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)

REGISTRATION_URL = os.getenv("REGISTRATION_SERVICE_URL", "http://localhost:5000")
WAITLIST_URL = os.getenv("WAITLIST_SERVICE_URL", "http://localhost:5003")

@app.route("/cancel-registration", methods=["POST"])
def cancel_registration():
    data = request.get_json()
    volunteer_id = data.get("volunteerID")
    event_id = data.get("eventID")

    if not volunteer_id or not event_id:
        return jsonify({
            "code": 400,
            "message": "volunteerID and eventID are required"
        }), 400

    # Step 1: Cancel the confirmed registration
    cancel_resp = requests.put(
        f"{REGISTRATION_URL}/registration/status",
        json={
            "volunteerID": volunteer_id,
            "eventID": event_id,
            "status": "cancelled"
        }
    )

    if cancel_resp.status_code != 200:
        return jsonify({
            "code": cancel_resp.status_code,
            "message": f"Failed to cancel registration: {cancel_resp.text}"
        }), cancel_resp.status_code

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
                "volunteerID": promoted_volunteer_id,
                "eventID": event_id,
                "status": "pending"
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
    app.run(port=5010, debug=True)