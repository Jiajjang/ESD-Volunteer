from dotenv import load_dotenv
from supabase import create_client
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

from flasgger import Swagger
swagger = Swagger(app)

# --- Swagger Configuration ---
app.config['SWAGGER'] = {
    'title': 'Volunteer Service API',
    'uiversion': 3,
    'definitions': {
        'Volunteer': {
            'type': 'object',
            'properties': {
                'volunteer_id': {'type': 'integer'},
                'volunteerName': {'type': 'string'},
                'email': {'type': 'string'},
                'phoneNumber': {'type': 'string'},
                'gender': {'type': 'string'},
                'password': {'type': 'string'},
                'created': {'type': 'string', 'format': 'date-time'},
                'modified': {'type': 'string', 'format': 'date-time'}
            }
        }
    }
}

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# 1. Get all volunteers
@app.route("/volunteer")
def get_all():
    """Get all volunteers
    ---
    tags:
      - Volunteer
    responses:
      200:
        description: List of all volunteers
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              type: object
              properties:
                volunteers:
                  type: array
                  items:
                    $ref: '#/definitions/Volunteer'
      404:
        description: No volunteers found
    """

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
    """Get a volunteer by ID
    ---
    tags:
      - Volunteer
    parameters:
      - in: path
        name: volunteer_id
        type: integer
        required: true
        description: ID of the volunteer
    responses:
      200:
        description: Volunteer found
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Volunteer'
      404:
        description: Volunteer not found
    """

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
    """Get a volunteer by email
    ---
    tags:
      - Volunteer
    parameters:
      - in: path
        name: email
        type: string
        required: true
        description: Email of the volunteer
    responses:
      200:
        description: Volunteer found
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Volunteer'
      404:
        description: Volunteer not found
    """

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
    """Create a new volunteer
    ---
    tags:
      - Volunteer
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - volunteerName
            - email
            - password
          properties:
            volunteerName:
              type: string
              example: John Doe
            phoneNumber:
              type: string
              example: "91234567"
            email:
              type: string
              example: john@example.com
            password:
              type: string
              example: password123
            gender:
              type: string
              example: M
    responses:
      201:
        description: Volunteer created
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Volunteer'
      400:
        description: Email already exists
      500:
        description: Internal server error
    """

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
    """Update a volunteer
    ---
    tags:
      - Volunteer
    parameters:
      - in: path
        name: volunteer_id
        type: integer
        required: true
        description: ID of the volunteer
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            volunteerName:
              type: string
            phoneNumber:
              type: string
            email:
              type: string
            gender:
              type: string
    responses:
      200:
        description: Volunteer updated
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Volunteer'
      404:
        description: Volunteer not found
      500:
        description: Internal server error
    """
    
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
