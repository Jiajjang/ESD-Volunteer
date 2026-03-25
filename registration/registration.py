from flask import Flask, request, jsonify
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
import pytz
import os
from dotenv import load_dotenv

# Timezone
sg_tz = pytz.timezone('Asia/Singapore')

# Load environment variables from .env
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials missing in .env")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# Helper to convert Supabase row to JSON-friendly format
def format_registration(reg):
    return {
        "registration_id": reg.get("registration_id"),
        "volunteer_id": reg.get("volunteer_id"),
        "email": reg.get("email"),
        "event_id": reg.get("event_id"),
        "status": reg.get("status"),
        "registered_at": reg.get("registered_at"),
        "expires_at": reg.get("expires_at")
    }

# HELPER FUNCTION TO GET DATA
def getData(filters: dict = None):
    query = supabase.table("registration").select("*")
    if filters:
        for key, value in filters.items():
            # Map camelCase to snake_case
            column = {
                "registration_id": "registration_id",
                "volunteer_id": "volunteer_id",
                "event_id": "event_id",
                "registered_at": "registered_at",
                "expires_at": "expires_at"
            }.get(key, key)
            query = query.eq(column, value)
    response = query.execute()
    return response.data or []

# [GET] RETRIEVE ALL REGISTRATION DETAILS
@app.route("/registration")
def get_all():
    registrationList = getData()
    if registrationList:
        return jsonify({
            "code": 200,
            "data": {"Registrations": [format_registration(r) for r in registrationList]}
        })
    else:
        return jsonify({
            "code": 404,
            "message": "There are no registrations."
        })

# [GET] RETRIEVE REGISTRATION BY EVENTID
@app.route("/registration/<int:event_id>")
def get_by_eventID(event_id):
    registrationList = getData({"event_id": event_id})
    if registrationList:
        return jsonify({
            "code": 200,
            "data": {"Registrations": [format_registration(r) for r in registrationList]}
        })
    else:
        return jsonify({
            "code": 400,
            "message": "Event not found"
        }), 400

# [POST] VOLUNTEER REGISTERS
@app.route("/registration", methods=["POST"])
def add_registration():
    data = request.get_json()

    checkStatus = getData({"volunteer_id": data["volunteer_id"], "event_id": data["event_id"]})
    if checkStatus and checkStatus[0]["status"] in ["confirmed", "pending"]:
        return jsonify({
            "code": 400,
            "message": "User already registered for this event"
        }), 400

    registration = {
        "volunteer_id": data["volunteer_id"],
        "email": data["email"],
        "event_id": data["event_id"],
        "status": "pending",  # need to call events service to check capacity first
        "registered_at": datetime.now(sg_tz).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    }

    supabase.table("registration").insert(registration).execute()

    return jsonify({
        "code": 201,
        "data": registration
    }), 201

# [DELETE] VOLUNTEER CANCEL REGISTRATION
@app.route("/registration", methods=["DELETE"])
def cancel_registration():
    data = request.get_json()
    deleted = supabase.table("registration")\
        .delete()\
        .eq("volunteer_id", data["volunteer_id"])\
        .eq("event_id", data["event_id"])\
        .execute()

    if deleted.data:
        return jsonify({
            "code": 200,
            "message": "Deletion Success"
        })
    else:
        return jsonify({
            "code": 400,
            "message": "User not found."
        }), 400

# [PUT] UPDATE VOLUNTEER STATUS (PENDING -> CONFIRMED)
@app.route("/registration", methods=["PUT"])
def update_registration():
    data = request.get_json()
    updated = supabase.table("registration")\
        .update({"status": "confirmed"})\
        .eq("volunteer_id", data["volunteer_id"])\
        .eq("event_id", data["event_id"])\
        .execute()

    if updated.data:
        return jsonify({
            "code": 200,
            "message": "User status updated successfully",
            "data": format_registration(updated.data[0])
        })
    else:
        return jsonify({
            "code": 400,
            "message": "User not found"
        }), 400

if __name__ == "__main__":
    app.run(port=5000, debug=True)