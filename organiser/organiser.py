from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

from flasgger import Swagger
swagger = Swagger(app)

# --- Swagger Configuration ---
app.config['SWAGGER'] = {
    'title': 'Organiser Service API',
    'uiversion': 3,
    'definitions': {
        'Organiser': {
            'type': 'object',
            'properties': {
                'organiser_id': {'type': 'integer'},
                'organiserName': {'type': 'string'},
                'email': {'type': 'string'},
                'phoneNumber': {'type': 'string'}
            }
        }
    }
}

supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

#1 Get all organisers
@app.route("/organiser", methods=['GET'])
def getAllOrganisers():
    """Get all organisers
    ---
    tags:
      - Organiser
    responses:
      200:
        description: List of all organisers
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              type: array
              items:
                $ref: '#/definitions/Organiser'
      404:
        description: No organisers found
      500:
        description: Internal server error
    """

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
    """Get an organiser by ID
    ---
    tags:
      - Organiser
    parameters:
      - in: path
        name: organiserID
        type: integer
        required: true
        description: ID of the organiser
    responses:
      200:
        description: Organiser found
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Organiser'
      404:
        description: Organiser not found
      500:
        description: Internal server error
    """

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
    """Get an organiser by email
    ---
    tags:
      - Organiser
    parameters:
      - in: path
        name: email
        type: string
        required: true
        description: Email of the organiser
    responses:
      200:
        description: Organiser found
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Organiser'
      404:
        description: Organiser not found
      500:
        description: Internal server error
    """

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
    """Create a new organiser
    ---
    tags:
      - Organiser
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - organiserName
            - email
          properties:
            organiserName:
              type: string
              example: Jane Smith
            email:
              type: string
              example: jane@example.com
            phoneNumber:
              type: string
              example: "98765432"
    responses:
      201:
        description: Organiser created
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Organiser'
      500:
        description: Internal server error
    """

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
    """Update an organiser by ID
    ---
    tags:
      - Organiser
    parameters:
      - in: path
        name: organiserID
        type: integer
        required: true
        description: ID of the organiser
      - in: body
        name: body
        required: true
        schema:
          $ref: '#/definitions/Organiser'
    responses:
      200:
        description: Organiser updated
        schema:
          type: object
          properties:
            code:
              type: integer
            data:
              $ref: '#/definitions/Organiser'
      404:
        description: Organiser not found
      500:
        description: Internal server error
    """
    
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