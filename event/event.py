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

# --- Supabase ---
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- RabbitMQ Config ---
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'guest')
FANOUT_EXCHANGE = os.environ.get('FANOUT_EXCHANGE', 'G2T7_fanout.exchange')

#Helper function for RabbitMQ --------------------
def publish_event_cancelled(event_id):
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        #declare the exchange, ensure it matches the Waitlist service
        channel.exchange_declare(exchange=FANOUT_EXCHANGE, exchange_type='fanout', durable=True)

        #create the message
        message = json.dumps({"event_id": event_id, "status": "cancelled"})

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
            "eventID": event_id, 
            "capacity": curr})
    except Exception as e:
        return jsonify({
            "code": 500, 
            "message": str(e)
        }), 500
    

#Scenario 3 Cancel Event (RabbitMQ Fanout)
@app.route("/event/<int:event_id>", methods=['DELETE'])
def delete_event(event_id):
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'No reason provided')

        # Update Supabase Status
        response = supabase.table('event').update({
            "status": "cancelled",
            "reason": reason
        }).eq('event_id', event_id).execute()

        if not response.data:
            return jsonify({
                "code": 404, 
                "message": "Event not found"
            }), 404

        # Publish to RabbitMQ (The Fanout Exchange)
        publish_event_cancelled(event_id)

        return jsonify({
            "code": 200,
            "eventID": event_id,
            "status": "cancelled",
            "reason": reason
        })
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)


