# /api/javascript_exec_api.py
from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
import subprocess, tempfile, os

javascript_exec_api = Blueprint('javascript_exec_api', __name__, url_prefix='/run')
api = Api(javascript_exec_api)

class JavaScriptExec(Resource):
    def post(self):
        """Executes submitted JavaScript code using Node.js inside the container."""
        data = request.get_json()
        code = data.get("code", "")

        if not code.strip():
            return {"output": "⚠️ No code provided."}, 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=".js") as tmp:
            tmp.write(code.encode())
            tmp.flush()

            try:
                result = subprocess.run(
                    ["node", tmp.name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                output = "⏱️ Execution timed out (5 s limit)."
            except Exception as e:
                output = f"⚠️ Error running JavaScript: {str(e)}"
            finally:
                os.unlink(tmp.name)

        return {"output": output}

api.add_resource(JavaScriptExec, "/javascript")