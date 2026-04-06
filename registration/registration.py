from flask import Flask, request, jsonify
from supabase import create_client, Client
from flask_cors import CORS
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
CORS(app)

from flasgger import Swagger
swagger = Swagger(app)

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
    """Get all registrations
    ---
    tags:
      - Registration
    responses:
      200:
        description: List of all registrations
      404:
        description: No registrations found
    """

    registrations = getData()
    if registrations:
        return jsonify({"code": 200, "data": {"Registrations": [format_registration(r) for r in registrations]}})
    return jsonify({"code": 404, "message": "No registrations found"}), 404

@app.route("/registration/<int:event_id>")
def get_by_event(event_id):
    """Get registrations by event ID
    ---
    tags:
      - Registration
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
        description: ID of the event
    responses:
      200:
        description: Registrations found
      400:
        description: Event not found
    """

    registrations = getData({"event_id": event_id})
    if registrations:
        return jsonify({"code": 200, "data": {"Registrations": [format_registration(r) for r in registrations]}})
    return jsonify({"code": 400, "message": "Event not found"}), 400

@app.route("/registration/<int:event_id>/emails")
def get_emails_by_event(event_id):
    """Get all registered emails for an event
    ---
    tags:
      - Registration
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
        description: ID of the event
    responses:
      200:
        description: List of emails
      404:
        description: No emails found
    """

    response = (
        supabase.table("registration")
        .select("email")
        .eq("event_id", event_id)
        .execute()
    )
    emails = [row["email"] for row in (response.data or []) if row.get("email")]
    if emails:
        return jsonify({
            "code": 200,
            "data": {
                "event_id": event_id,
                "emails": emails
            }
        }), 200
    return jsonify({
        "code": 404,
        "message": "No emails found for this event"
    }), 404

@app.route("/registration/<int:event_id>/<int:volunteer_id>")
def get_by_event_and_volunteer(event_id, volunteer_id):
    """Get registration by event ID and volunteer ID
    ---
    tags:
      - Registration
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
      - in: path
        name: volunteer_id
        type: integer
        required: true
    responses:
      200:
        description: Registration found
      400:
        description: Not found
    """

    registrations = getData({"event_id": event_id, "volunteer_id" : volunteer_id})
    if registrations:
        return jsonify({"code": 200, "data": {"Registrations": [format_registration(r) for r in registrations]}})
    return jsonify({"code": 400, "message": "Event not found"}), 400

@app.route("/registration/volunteer/<int:volunteer_id>")
def get_by_volunteer(volunteer_id):
    """Get registrations by volunteer ID
    ---
    tags:
      - Registration
    parameters:
      - in: path
        name: volunteer_id
        type: integer
        required: true
    responses:
      200:
        description: Registrations found
      400:
        description: Not found
    """

    registrations = getData({ "volunteer_id" : volunteer_id})
    if registrations:
        return jsonify({"code": 200, "data": {"Registrations": [format_registration(r) for r in registrations]}})
    return jsonify({"code": 400, "message": "Event not found"}), 400

# ─── POST ───
@app.route("/registration", methods=["POST"])
def add_registration():
    """Create a new registration
    ---
    tags:
      - Registration
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - volunteer_id
            - email
            - event_id
          properties:
            volunteer_id:
              type: integer
              example: 1
            email:
              type: string
              example: john@example.com
            event_id:
              type: integer
              example: 3
            status:
              type: string
              enum: [confirmed, waitlisted, pending]
              example: confirmed
            expires_at:
              type: string
              example: "2026-04-05 12:00:00"
    responses:
      201:
        description: Registration created
      400:
        description: User already registered
    """

    data = request.get_json()
    # existing = getData({"volunteer_id": data["volunteer_id"], "event_id": data["event_id"]})
    # if existing and existing[0]["status"] in ["confirmed", "waitlisted"]:
    #     return jsonify({"code": 400, "message": "User already registered"}), 400
    
    existing = getData({
        "volunteer_id": data["volunteer_id"],
        "event_id": data["event_id"]
    })

    # 🔥 block ANY active registration (not just first record)
    if existing:
        active = [
            r for r in existing
            if r["status"] in ["confirmed", "pending", "waitlisted"]
        ]
        if active:
            return jsonify({
                "code": 400,
                "message": "User already has an active registration"
            }), 400

    registration = {
        "volunteer_id": data["volunteer_id"],
        "email":        data["email"],
        "event_id":     data["event_id"],
        "status":       data.get("status", "confirmed"),  # ← use what composite sends
        "registered_at": datetime.now(sg_tz).strftime('%Y-%m-%d %H:%M:%S'),
        "expires_at":   data.get("expires_at") if data.get("status") == "pending" else None #felicia
    }

    result = supabase.table("registration").insert(registration).execute()
    return jsonify({"code": 201, "data": result.data[0]}), 201

# ─── DELETE ───
@app.route("/registration", methods=["DELETE"])
def cancel_registration():
    """Cancel a registration (sets status to cancelled, keeps record)
    ---
    tags:
      - Registration
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
              example: 1
            event_id:
              type: integer
              example: 3
    responses:
      200:
        description: Registration cancelled
      400:
        description: User not found
    """
    data = request.get_json()
    updated = supabase.table("registration")\
        .update({"status": "cancelled", "expires_at": None})\
        .eq("volunteer_id", data["volunteer_id"])\
        .eq("event_id", data["event_id"])\
        .execute()
    if updated.data:
        return jsonify({
            "code": 200,
            "message": "Registration cancelled successfully",
            "data": format_registration(updated.data[0])
        })
    return jsonify({"code": 400, "message": "User not found"}), 400
    
# ─── PUT (update to confirmed) ───
@app.route("/registration", methods=["PUT"])
def update_registration():
    """Update registration status to confirmed
    ---
    tags:
      - Registration
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
              example: 1
            event_id:
              type: integer
              example: 3
    responses:
      200:
        description: Status updated to confirmed
      400:
        description: User not found
    """

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
    volunteer_id = data.get("volunteer_id")
    event_id = data.get("event_id")
    status = data.get("status")
    expires_at = data.get("expires_at")

    if not all([volunteer_id, event_id, status]):
        return jsonify({
            "code": 400,
            "message": "volunteer_id, event_id, and status are required"
        }), 400

    # Get latest registration
    latest = supabase.table("registration") \
        .select("*") \
        .eq("volunteer_id", volunteer_id) \
        .eq("event_id", event_id) \
        .order("registered_at", desc=True) \
        .limit(1) \
        .execute()

    if not latest.data:
        return jsonify({"code": 400, "message": "User not found"}), 400

    latest_id = latest.data[0]["registration_id"]

    # Update ONLY latest record
    updated = supabase.table("registration") \
        .update({
            "status": status,
            "expires_at": expires_at if status == "pending" else None
        }) \
        .eq("registration_id", latest_id) \
        .execute()

    # Cancel all other records
    supabase.table("registration") \
        .update({
            "status": "cancelled",
            "expires_at": None
        }) \
        .eq("volunteer_id", volunteer_id) \
        .eq("event_id", event_id) \
        .neq("registration_id", latest_id) \
        .execute()

    return jsonify({
        "code": 200,
        "message": "Latest registration updated successfully",
        "data": format_registration(updated.data[0])
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)