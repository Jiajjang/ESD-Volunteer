from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.chnmdovubaorrcrwborm:ESDproject213!@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

db = SQLAlchemy(app)

class Organiser(db.Model):
    __tablename__ = 'organiser'

    organiserid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    organisername = db.Column(db.String(255), nullable=False)
    phonenumber = db.Column(db.String(8))
    registeredaddress = db.Column(db.String(255))
    uen = db.Column(db.String(50))

    def __init__(self, email, password, organisername, phonenumber=None, uen=None, registeredaddress=None):
        self.email = email
        self.password = password
        self.organisername = organisername
        self.phonenumber = phonenumber
        self.uen = uen
        self.registeredaddress = registeredaddress

    def json(self):
        return {
            "organiserID": self.organiserid,
            "email": self.email,
            "password": self.password,
            "organiserName": self.organisername,
            "phoneNumber": self.phonenumber,
            "UEN": self.uen,
            "registeredAddress": self.registeredaddress
        }

#1 Get all organisers
@app.route("/organiser", methods=['GET'])
def getAllOrganisers():
    organisers = db.session.scalars(db.select(Organiser)).all()
    if organisers:
        return jsonify({"code": 200, "data": [o.json() for o in organisers]})
    return jsonify({"code": 404, "message": "No organisers found."}), 404

#2 Get one organiser by ID
@app.route("/organiser/<int:organiserID>", methods=['GET'])
def getOrganiserByID(organiserID):
    organiser = db.session.get(Organiser, organiserID)
    if organiser:
        return jsonify({"code": 200, "data": organiser.json()})
    return jsonify({"code": 404, "message": "Organiser not found."}), 404

#3 Get one organiser by email (useful for login)
@app.route("/organiser/login", methods=['POST'])
def getOrganiserByEmail():
    data = request.get_json()
    organiser = db.session.scalar(
        db.select(Organiser).filter_by(email=data['email'], password=data['password'])
    )
    if organiser:
        return jsonify({"code": 200, "data": organiser.json()})
    return jsonify({"code": 401, "message": "Invalid credentials."}), 401

#4 Create organiser
@app.route("/organiser", methods=['POST'])
def createOrganiser():
    data = request.get_json()
    organiser = Organiser(**data)
    try:
        db.session.add(organiser)
        db.session.commit()
        return jsonify({"code": 201, "data": organiser.json()}), 201
    except Exception as e:
        return jsonify({"code": 500, "message": "Error creating organiser: " + str(e)}), 500
    
#5 Update organiser by ID
@app.route("/organiser/<int:organiserID>", methods=['PUT'])
def updateOrganiserDetails(organiserID):
    organiser = db.session.get(Organiser, organiserID)
    if not organiser:
        return jsonify({"code": 404, "message": "Organiser not found."}), 404
    
    data = request.get_json()
    if 'organisername' in data:
        organiser.organisername = data['organisername']
    if 'email' in data:
        organiser.email = data['email']
    if 'password' in data:
        organiser.password = data['password']
    if 'uen' in data:
        organiser.uen = data['uen']
    if 'registeredaddress' in data:
        organiser.registeredaddress = data['registeredaddress']
    
    try:
        db.session.commit()
        return jsonify({"code": 200, "data": organiser.json()})
    except Exception as e:
        return jsonify({"code": 500, "message": "Error updating organiser: " + str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)