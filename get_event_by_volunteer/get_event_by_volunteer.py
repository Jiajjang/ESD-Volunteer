from flask import Flask, request, jsonify
from flask_cors import CORS
import pika, json, os, requests
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

from flasgger import Swagger
swagger = Swagger(app)

# --- Swagger Configuration ---
app.config['SWAGGER'] = {
    'title': 'Volunteer Event Aggregator API',
    'description': 'Composite service that combines Registration and Event data to show a volunteer\'s schedule.',
    'uiversion': 3,
    'definitions': {
        'EnrichedEvent': {
            'type': 'object',
            'properties': {
                'event_id': {'type': 'integer'},
                'name': {'type': 'string'},
                'start_date': {'type': 'string'},
                'end_date': {'type': 'string'},
                'location': {'type': 'string'},
                'registration_id': {'type': 'integer'},
                'registration_status': {
                    'type': 'string',
                    'enum': ['confirmed', 'pending', 'waitlisted']
                }
            }
        }
    }
}

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ── Atomic service URLs ──────────────────────────────────────────
REGISTRATION_URL = os.getenv("REGISTRATION_URL",  "http://registration:5000")
EVENT_URL        = os.getenv("EVENT_URL",         "http://event:5001")
# VOLUNTEER_URL    = os.getenv("VOLUNTEER_URL",     "http://volunteer:5002")
# WAITLIST_URL     = os.getenv("WAITLIST_URL",      "http://waitlist:5003")


@app.route("/get_event_by_volunteer/<int:volunteer_id>", methods=["GET"])
def get_event_by_volunteer(volunteer_id):
    """Get all events a volunteer is registered for 
    ---
    tags:
      - Volunteer Schedule
    parameters:
      - in: path
        name: volunteer_id
        type: integer
        required: true
        description: ID of the volunteer
    responses:
      200:
        description: Successfully retrieved enriched event list
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              type: object
              properties:
                events:
                  type: array
                  items:
                    $ref: '#/definitions/EnrichedEvent'
      404:
        description: No active registrations found
    """
    
    registrations_resp = requests.get(f"{REGISTRATION_URL}/registration/volunteer/{volunteer_id}")

    if registrations_resp.status_code != 200:
        registrations = []
    else:
        registrations = registrations_resp.json().get("data", {}).get("Registrations", [])
    vol_events = []

  # For each event volunteer is registered in, get the event details
    for reg in registrations:
        event_id = reg.get("event_id")
        registration_id = reg.get("registration_id")
        status = reg.get("status")

        if not event_id:
            continue

        if status in ("cancelled", "rejected"):
            continue

        events_resp = requests.get(f"{EVENT_URL}/event/{event_id}")
        if events_resp.status_code != 200:
            continue

        event = events_resp.json().get("data")
        if event:
            event["registration_status"] = status
            event["registration_id"] = registration_id
            vol_events.append(event)

    return jsonify({
        "code": 200,
        "data": {
            "events": vol_events
        }
    }), 200
            
if __name__ == "__main__":
    print("Get event by volunteer composite microservice running...")
    app.run(host="0.0.0.0", port=5012, debug=True)