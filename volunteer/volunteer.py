from dotenv import load_dotenv
from supabase import create_client
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# 1. Get all volunteers
@app.route("/volunteer")
def get_all():
    response = supabase.table("volunteer").select("*").execute()
    volunteers = response.data

    if volunteers:
        return jsonify({"code": 200, "data": {"volunteers": volunteers}})
    
    return jsonify({
        "code": 404, 
        "message": "There are no volunteers."
        }), 404


# 2. Get volunteer by ID
@app.route("/volunteer/<int:volunteer_id>")
def get_by_id(volunteer_id):
    response = supabase.table("volunteer").select("*").eq("volunteer_id", volunteer_id).execute()
    volunteer = response.data

    if volunteer:
        return jsonify({"code": 200, "data": volunteer[0]})
    
    return jsonify({
        "code": 404, 
        "message": "Volunteer not found."
        }), 404


# 3. Get volunteer by email
@app.route("/volunteer/<string:email>")
def get_by_email(email):
    response = supabase.table("volunteer").select("*").eq("email", email).execute()
    volunteer = response.data

    if volunteer:
        return jsonify({"code": 200, "data": volunteer[0]})
    
    return jsonify({
        "code": 404, 
        "message": "Volunteer not found."
        }), 404


# 4. Create volunteer
@app.route("/volunteer", methods=['POST'])
def create_volunteer():
    data = request.get_json()

    # check if email exists
    existing = supabase.table("volunteer").select("*").eq("email", data['email']).execute()
    if existing.data:
        return jsonify({"code": 400, "message": "Email already exists."}), 400

    volunteer = {
        "volunteerName": data['volunteerName'],
        "phoneNumber": data.get('phoneNumber'),
        "email": data['email'],
        "password": data['password'],
        "gender": data.get('gender'),
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat()
    }

    try:
        response = supabase.table("volunteer").insert(volunteer).execute()
        return jsonify({"code": 201, "data": response.data[0]}), 201
    except Exception as e:
        return jsonify({"code": 500, "message": "Error creating volunteer: " + str(e)}), 500


# 5. Update volunteer
@app.route("/volunteer/<int:volunteer_id>", methods=['PUT'])
def update_volunteer(volunteer_id):
    data = request.get_json()

    data['modified'] = datetime.now().isoformat()

    try:
        response = supabase.table("volunteer").update(data).eq("volunteer_id", volunteer_id).execute()
        if response.data:
            return jsonify({"code": 200, "data": response.data[0]})
        return jsonify({"code": 404, "message": "Volunteer not found."}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": "Error updating volunteer: " + str(e)}), 500


if __name__ == '__main__':
    print("Flask with Supabase: manage volunteers...")
    app.run(host='0.0.0.0', port=5002, debug=True)
