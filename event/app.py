import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from event import db, Event
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

#Scenrio 1 & 2: update the capacity 
#using HTTP PUT
@app.route("/event/<int:event_id>/capacity", methods=['PUT'])
def update_capacity(event_id):
    data = request.get_json()
    action = data.get('action') #whether increment or decrement

    #select event by id
    event = Event.query.get(event_id)

    if not event:
        return jsonify({
            "code": 404, 
            "message": "Event not found"
        }), 404
    
    if action == 'increment':
        if event.current_capacity < event.max_capacity:
            event.current_capacity +=1
        else:
            return jsonify({
                "code": 400, 
                "message": "Event is full"
            }), 400
        
    elif action == 'decrement':
        if event.current_capacity >0:
            event.current_capacity -=1

    db.session.commit()
    return jsonify({
        "code": 200, 
        "eventID": event.event_id, 
        "capacity": event.current_capacity
    }), 200

#Scenario 3: organiser cancel event
#using HTTP DELETE
@app.route("/event/<int:event_id>", methods=['DELETE'])
def delete_event(event_id):
    event = Event.query.get(event_id)
    
    if not event:
        return jsonify({
            "code": 404, 
            "message": "Event not found"
        }), 404

    event.status = 'DELETED'
    db.session.commit()

    return jsonify({
        "code": 200,
        "eventID": event.event_id,
        "status": "DELETED"
    }), 200


#if want to get all the events
@app.route("/event")
def get_all():
    event_list = Event.query.all()
    #if there are any events in the list then return with code 200, or else return not found with code 404
    if len(event_list):
        return jsonify({
            "code": 200, 
            "data": [e.json() for e in event_list]
        })
    return jsonify({
        "code": 404, 
        "message": "No events found"
    }), 404



if __name__ == '__main__':
    app.run(port=5001, debug=True) 
