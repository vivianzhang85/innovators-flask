from flask import Blueprint, request, jsonify, current_app
from flask_restful import Api, Resource
import requests

groq_api = Blueprint('groq_api', __name__, url_prefix='/api')
api = Api(groq_api)

class GroqAPI:
    
    class _Generate(Resource):
        def post(self):
            body = request.get_json()
            messages = body.get('messages')

            if not messages:
                return {'message': 'Missing "messages" in request body'}, 400

            api_key = current_app.config.get('GROQ_API_KEY')
            if not api_key:
                return {'message': 'API key not configured'}, 500

            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        "model": "llama3-8b-8192",
                        "messages": messages,
                        "temperature": 0.7
                    }
                )
                response.raise_for_status()
                return jsonify(response.json())
            except Exception as e:
                return {'message': f'Error contacting Groq API: {str(e)}'}, 500

    api.add_resource(_Generate, '/groq')