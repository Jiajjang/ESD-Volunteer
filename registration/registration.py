from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import pytz
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)
# If using Transaction Pooler or Session Pooler, we want to ensure we disable SQLAlchemy client side pooling -
# https://docs.sqlalchemy.org/en/20/core/pooling.html#switching-pool-implementations
# engine = create_engine(DATABASE_URL, poolclass=NullPool)

# Test the connection
try:
    with engine.connect() as connection:
        print("Connection successful!")
except Exception as e:
    print(f"Failed to connect: {e}")


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

db = SQLAlchemy(app)

class Registration(db.Model):
    __tablename__ = "registration"
    registrationID = db.Column(db.Integer, primary_key = True)
    volunteerID = db.Column(db.Integer, nullable = False)
    email = db.Column(db.String(50),nullable = False)
    eventID = db.Column(db.Integer,nullable = False)
    status = db.Column(db.String(25),nullable = False)
    registeredAt = db.Column(db.DateTime,nullable = False)
    expiresAt = db.Column(db.DateTime,nullable = False)
    
    def __init__(self, volunteerID, email, eventID, status, registeredAt, expiresAt):
        # self.registrationID = registrationID
        self.volunteerID = volunteerID
        self.email = email
        self.eventID = eventID
        self.status = status
        self.registeredAt = registeredAt
        self.expiresAt = expiresAt

    def json(self):
        return {
            "registrationID": self.registrationID, 
            "volunteerID": self.volunteerID, 
            "email": self.email, 
            "eventID": self.eventID,
            "status": self.status, 
            "registeredAt": self.registeredAt,
            "expiresAt": self.expiresAt
        }

# HELPER FUNCTION TO GET DATA
def getData(filters : dict = None):
    stmt = db.select(Registration)
    if filters:
        stmt = stmt.filter_by(**filters)
    return db.session.scalars(stmt)

# [GET] RETRIEVE ALL REGISTRATION DETAILS ------------
@app.route("/registration")
def get_all():
    registrationList = getData().all()
    if len(registrationList):
        return jsonify(
            {
                "code": 200,
                "data": {
                    "Registrations": [registration.json() for registration in registrationList]
                }
            }
        )
    else:
        return jsonify({
            "code":404,
            "message": "There are no registrations."
        })

# [GET] RETRIEVE REGISTRATION BY EVENTID
@app.route("/registration/<int:eventID>")
def get_by_eventID(eventID):
    registrationList = getData({"eventID" : eventID})
    if registrationList:
        return jsonify(
            {
                "code": 200,
                "data": {
                    "Registrations": [registration.json() for registration in registrationList]
                }
            }
        )
    else:
        return jsonify(
            {
            "code": 400,
            "message": "Event not found"
            }
        ), 400

# [POST] VOLUNTEER REGISTERS  -------------
@app.route("/registration", methods=["POST"])
def add_registration():
    data = request.get_json()
    checkStatus = getData({"volunteerID" : data["volunteerID"], "eventID" : data["eventID"]}).one_or_none()
    if checkStatus:
        if checkStatus.status in ["confirmed","pending"]:
            return jsonify(
                {
                    "code": 400,
                    "message": "User already registered for this event"
                }
            ), 400

    registration = Registration(
    volunteerID =data['volunteerID'],
    email =data['email'],
    eventID =data['eventID'],
    status ='pending', # need to call events service to check capacity first.
    registeredAt =datetime.now(sg_tz),
    expiresAt=datetime.now(timezone.utc) + timedelta(days=1)
)
    try: 
        db.session.add(registration)
        db.session.commit()
    except:
        return jsonify({
            "code": 500,
            "message":"An error occured while registering user"
        }), 500
        
    return jsonify({
        "code":201,
        "data": registration.json()
    }), 201
        

# [DELETE] VOLUNTEER CANCEL REGISTRATION ----------
@app.route("/registration",methods=["DELETE"])
def cancel_registration():
    data = request.get_json()
    user = getData({"volunteerID" : data["volunteerID"], "eventID" :data["eventID"]}).one_or_none()
    if user:
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({
                "code":200,
                "message": "Deletion Success"
            })
        except:
            db.session.rollback()
            return jsonify({
                "code": 500,
                "message": "An error occured while deleting user"
            }), 500
    else:
        return jsonify({
            "code": 400,
            "message": "User not found."
        }),400
        
# [PUT] UPDATE VOLUNTEER STATUS (PENDING -> CONFIRMED) ------------
@app.route("/registration", methods=["PUT"])
def update_registration():
    data = request.get_json()
    checkUser = getData({"volunteerID": data["volunteerID"], "eventID":data["eventID"]}).one_or_none()
    if not checkUser:
        return jsonify({
            "code": 400,
            "message": "User not found"
        }), 400
    else:
        checkUser.status = "confirmed"
        db.session.commit()
        return jsonify({
            "code": 200,
            "message": "User status updated successfully",
            "data" : checkUser.json()
        })
        

if __name__ == '__main__':
    app.run(port=5000, debug = True)