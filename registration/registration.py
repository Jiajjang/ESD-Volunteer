from flask import Flask, request, jsonify
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
import pytz, os
from dotenv import load_dotenv

# Timezone
sg_tz = pytz.timezone('Asia/Singapore')

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials missing in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# Helper to convert Supabase row to JSON
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

def getData(filters: dict = None):
    query = supabase.table("registration").select("*")
    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)
    response = query.execute()
    return response.data or []

# ─── GET ───
@app.route("/registration")
def get_all():
    registrations = getData()
    if registrations:
        return jsonify({"code": 200, "data": {"Registrations": [format_registration(r) for r in registrations]}})
    return jsonify({"code": 404, "message": "No registrations found"}), 404

@app.route("/registration/<int:event_id>")
def get_by_event(event_id):
    registrations = getData({"event_id": event_id})
    if registrations:
        return jsonify({"code": 200, "data": {"Registrations": [format_registration(r) for r in registrations]}})
    return jsonify({"code": 400, "message": "Event not found"}), 400

@app.route("/registration/<int:event_id>/<int:volunteer_id>")
def get_by_event_and_volunteer(event_id, volunteer_id):
    registrations = getData({"event_id": event_id, "volunteer_id" : volunteer_id})
    if registrations:
        return jsonify({"code": 200, "data": {"Registrations": [format_registration(r) for r in registrations]}})
    return jsonify({"code": 400, "message": "Event not found"}), 400

# ─── POST ───
@app.route("/registration", methods=["POST"])
def add_registration():
    data = request.get_json()
    existing = getData({"volunteer_id": data["volunteer_id"], "event_id": data["event_id"]})
    if existing and existing[0]["status"] in ["confirmed", "waitlisted"]:
        return jsonify({"code": 400, "message": "User already registered"}), 400

    registration = {
        "volunteer_id": data["volunteer_id"],
        "email":        data["email"],
        "event_id":     data["event_id"],
        "status":       data.get("status", "confirmed"),  # ← use what composite sends
        "registered_at": datetime.now(sg_tz).isoformat(),
        "expires_at":   None                              # ← always null
    }

    result = supabase.table("registration").insert(registration).execute()
    return jsonify({"code": 201, "data": result.data[0]}), 201

# @app.route("/registration", methods=["POST"])
# def add_registration():
#     data = request.get_json()
#     existing = getData({"volunteer_id": data["volunteer_id"], "event_id": data["event_id"]})
#     if existing and existing[0]["status"] in ["confirmed", "pending"]:
#         return jsonify({"code": 400, "message": "User already registered"}), 400

#     registration = {
#         "volunteer_id": data["volunteer_id"],
#         "email": data["email"],
#         "event_id": data["event_id"],
#         "status": data["status"],
#         "registered_at": datetime.now(sg_tz).isoformat(),
#         "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
#     }

#     supabase.table("registration").insert(registration).execute()
#     print(type(registration), registration)
#     data = registration[0] if isinstance(registration, list) else registration
#     return jsonify({"code": 201, "data": data}), 201

# ─── DELETE ───
@app.route("/registration", methods=["DELETE"])
def cancel_registration():
    data = request.get_json()
    deleted = supabase.table("registration")\
        .delete()\
        .eq("volunteer_id", data["volunteer_id"])\
        .eq("event_id", data["event_id"])\
        .execute()
    if deleted.data:
        return jsonify({"code": 200, "message": "Deletion Success"})
    return jsonify({"code": 400, "message": "User not found"}), 400

# ─── PUT (update to confirmed) ───
@app.route("/registration", methods=["PUT"])
def update_registration():
    data = request.get_json()
    updated = supabase.table("registration")\
        .update({"status": "confirmed"})\
        .eq("volunteer_id", data["volunteer_id"])\
        .eq("event_id", data["event_id"])\
        .execute()
    if updated.data:
        return jsonify({"code": 200, "message": "User status updated successfully", "data": format_registration(updated.data[0])})
    return jsonify({"code": 400, "message": "User not found"}), 400

# ─── PUT /registration/status (used by composite) ───
@app.route("/registration/status", methods=["PUT"])
def update_registration_status():
    data = request.get_json()
    volunteer_id = data.get("volunteerID")
    event_id = data.get("eventID")
    status = data.get("status")

    if not all([volunteer_id, event_id, status]):
        return jsonify({"code": 400, "message": "volunteerID, eventID, and status are required"}), 400

    updated = supabase.table("registration")\
        .update({"status": status})\
        .eq("volunteer_id", volunteer_id)\
        .eq("event_id", event_id)\
        .execute()

    if updated.data:
        return jsonify({
            "code": 200,
            "message": "User status updated successfully",
            "data": format_registration(updated.data[0])
        })
    return jsonify({"code": 400, "message": "User not found"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)