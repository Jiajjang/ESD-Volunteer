import os
import json
import pika
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

from flasgger import Swagger
swagger = Swagger(app)

# --- Swagger Configuration ---
app.config['SWAGGER'] = {
    'title': 'Event Service API',
    'uiversion': 3,
    'definitions': {
        'Event': {
            'type': 'object',
            'properties': {
                'event_id': {'type': 'integer'},
                'name': {'type': 'string'},
                'organiser_id': {'type': 'integer'},
                'start_date': {'type': 'string', 'format': 'date-time'},
                'end_date': {'type': 'string', 'format': 'date-time'},
                'max_capacity': {'type': 'integer'},
                'current_capacity': {'type': 'integer'},
                'status': {'type': 'string', 'enum': ['open', 'closed', 'cancelled']},
                'reason': {'type': 'string'}
            }
        }
    }
}

# --- Supabase ---
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- RabbitMQ Config ---
RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST", "active-white-bear-01.rmq6.cloudamqp.com")
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "ntxsydfp")
RABBITMQ_USER  = os.getenv("RABBITMQ_USER", "ntxsydfp")
RABBITMQ_PASS  = os.getenv("RABBITMQ_PASS", "VRMsjW_248ItCPA3gSjNFl51HfiO1Dt9")
FANOUT_EXCHANGE = os.getenv("FANOUT_EXCHANGE","G2T7_fanout.exchange")

#Helper function for RabbitMQ --------------------
def publish_event_cancelled(event_id, event_name, start_date, end_date):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, virtual_host=RABBITMQ_VHOST, credentials=credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        #declare the exchange, ensure it matches the Waitlist service
        channel.exchange_declare(exchange=FANOUT_EXCHANGE, exchange_type='fanout', durable=True)

        #create the message
        message = json.dumps({"event_id": event_id, "event_name" : event_name, "start_date": start_date, "end_date": end_date})

        #publish
        channel.basic_publish(exchange=FANOUT_EXCHANGE, routing_key='', body=message)
        connection.close()
        print(f" [AMQP] Sent Event Cancellation for ID: {event_id}")
    except Exception as e:
        print(f" [AMQP] Error publishing message: {e}")

# ------

#Get All Events
@app.route("/event", methods=['GET'])
def get_all():
    """Get all events
    ---
    tags:
      - Event
    responses:
      200:
        description: List of all events
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              type: array
              items:
                $ref: '#/definitions/Event'
      404:
        description: No events found
    """
    try:
        response = supabase.table('event').select('*').execute()
        if response.data:
            return jsonify({
                "code": 200, 
                "data": response.data})
        return jsonify({
            "code": 404, 
            "message": "No events found"
        }), 404
    except Exception as e:
        return jsonify({
            "code": 500, 
            "message": str(e)
        }), 500

#Get Event by ID
@app.route("/event/<int:event_id>", methods=['GET'])
def get_by_id(event_id):
    """Get an event by ID
    ---
    tags:
      - Event
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
    responses:
      200:
        description: Event found
        schema:
          type: object
          properties:
            code: {type: integer}
            data: {$ref: '#/definitions/Event'}
      404:
        description: Event not found
    """

    try:
        response = supabase.table('event').select('*').eq('event_id', event_id).execute()
        if response.data:
            return jsonify({"code": 200, "data": response.data[0]})
        return jsonify({"code": 404, "message": "Event not found"}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500


# Get Event by OrganiserId
@app.route("/event/organiser/<int:organiser_id>", methods=['GET'])
def get_by_organiser(organiser_id):
    """Get events by organiser ID
    ---
    tags:
      - Event
    parameters:
      - in: path
        name: organiser_id
        type: integer
        required: true
    responses:
      200:
        description: Events found
        schema:
          type: object
          properties:
            code: {type: integer}
            data:
              type: array
              items:
                $ref: '#/definitions/Event'
      404:
        description: No events found for this organiser
    """

    try:
        response = (
            supabase.table('event').select('*').eq('organiser_id', organiser_id).execute()
        )

        if response.data:
            return jsonify({
                "code": 200,
                "data": response.data
            }), 200

        return jsonify({
            "code": 404,
            "message": "No events found for this organiser",
            "data": []
        }), 404

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": str(e)
        }), 500

#Scenario 1 and 2 Update Capacity
@app.route("/event/<int:event_id>/capacity", methods=['PUT'])
def update_capacity(event_id):
    """Increment or decrement event capacity
    ---
    tags:
      - Event
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [action]
          properties:
            action:
              type: string
              enum: [increment, decrement]
              example: increment
    responses:
      200:
        description: Capacity updated
        schema:
          type: object
          properties:
            code: {type: integer}
            event_id: {type: integer}
            capacity: {type: integer}
      400:
        description: Event is full
    """

    try:
        data = request.get_json()
        action = data.get('action')

        # Get current state
        res = supabase.table('event').select('current_capacity, max_capacity').eq('event_id', event_id).execute()
        if not res.data:
            return jsonify({
                "code": 404, 
                "message": "Event not found"
            }), 404
        
        event = res.data[0]
        curr = event['current_capacity']
        mx = event['max_capacity']

        # the action has to be declared inorder to update the capacity (increment/decrement)
        if action == 'increment':
            if curr < mx:
                curr += 1
            else:
                return jsonify({
                    "code": 400, 
                    "message": "Event is full"
                }), 400
        elif action == 'decrement':
            if curr > 0:
                curr -= 1

        # Update Supabase
        update_res = supabase.table('event').update({"current_capacity": curr}).eq('event_id', event_id).execute()
        return jsonify({
            "code": 200, 
            "event_id": event_id, 
            "capacity": curr})
    except Exception as e:
        return jsonify({
            "code": 500, 
            "message": str(e)
        }), 500
    

#Scenario 3 Cancel Event (RabbitMQ Fanout)
@app.route("/event/delete/<int:event_id>", methods=['DELETE'])
def delete_event(event_id):
    """Cancel an event and notify all services via RabbitMQ
    ---
    tags:
      - Event
    parameters:
      - in: path
        name: event_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            reason:
              type: string
              example: Bad weather conditions
    responses:
      200:
        description: Event cancelled
        schema:
          type: object
          properties:
            code: {type: integer}
            status: {type: string}
            reason: {type: string}
    """

    print("======== DELETE ROUTE ENTERED ========", flush=True)
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', 'No reason provided')

        # Update Supabase Status
        event_result = supabase.table('event').select(
            "event_id, name, start_date, end_date"
        ).eq('event_id', event_id).execute()

        if not event_result.data:
            return jsonify({
                "code": 404,
                "message": "Event not found"
            }), 404

        event_row = event_result.data[0]
        event_name = event_row.get("name")
        start_date = event_row.get("start_date")
        end_date = event_row.get("end_date")

        supabase.table('event').update({
            "status": "cancelled",
            "reason": reason
        }).eq('event_id', event_id).execute()
        
        # Publish to RabbitMQ (The Fanout Exchange)
        publish_event_cancelled(event_id, event_name, start_date, end_date)

        return jsonify({
            "code": 200,
            "event_id": event_id,
            "event_name": event_name,
            "start_date": start_date,
            "end_date": end_date,
            "status": "cancelled",
            "reason": reason
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)