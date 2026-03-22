from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

#1 Get all organisers
@app.route("/organiser", methods=['GET'])
def getAllOrganisers():
    try:
        response = supabase.table('organiser').select('*').execute()
        if response.data:
            return jsonify({"code": 200, "data": response.data})
        return jsonify({"code": 404, "message": "No organisers found."}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

#2 Get organiser by ID
@app.route("/organiser/<int:organiserID>", methods=['GET'])
def getOrganiserByID(organiserID):
    try:
        response = supabase.table('organiser').select('*').eq('organiser_id', organiserID).execute()
        if response.data:
            return jsonify({"code": 200, "data": response.data[0]})
        return jsonify({"code": 404, "message": "Organiser not found."}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

#3 Get organiser by email
@app.route("/organiser/<string:email>", methods=['GET'])
def getOrganiserByEmail(email):
    try:
        response = supabase.table('organiser').select('*').eq('email', email).execute()
        if response.data:
            return jsonify({"code": 200, "data": response.data[0]})
        return jsonify({"code": 404, "message": "Organiser not found."}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

#4 Create organiser
@app.route("/organiser", methods=['POST'])
def createOrganiser():
    try:
        data = request.get_json()
        response = supabase.table('organiser').insert(data).execute()
        if response.data:
            return jsonify({"code": 201, "data": response.data[0]}), 201
        return jsonify({"code": 500, "message": "Error creating organiser."}), 500
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

#5 Update organiser by ID
@app.route("/organiser/<int:organiserID>", methods=['PUT'])
def updateOrganiserDetails(organiserID):
    try:
        data = request.get_json()
        response = supabase.table('organiser').update(data).eq('organiser_id', organiserID).execute()
        if response.data:
            return jsonify({"code": 200, "data": response.data[0]})
        return jsonify({"code": 404, "message": "Organiser not found."}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)