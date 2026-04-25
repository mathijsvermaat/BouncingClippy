import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from azure.identity import ManagedIdentityCredential
 
load_dotenv()
 
app = Flask(__name__)
 
CLIPPY_SYSTEM_MESSAGE = (
    "You are Clippy, the iconic Microsoft Office assistant! "
    "You're helpful, friendly, and enthusiastic. "
    "You love to assist users with their questions and always try to be encouraging. "
    "Keep your responses concise and helpful."
)
 
chat_sessions = {}
 
 
class BouncingClippy:
    def __init__(self):
        self.endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")
        self.model_name = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o")
 
        if not self.endpoint:
            raise ValueError("Missing required environment variable: AZURE_AI_FOUNDRY_ENDPOINT")
 
        self.credential = ManagedIdentityCredential()
        self.history = [
            {"role": "system", "content": CLIPPY_SYSTEM_MESSAGE}
        ]
 
    def send_message(self, user_prompt: str) -> str:
        self.history.append({"role": "user", "content": user_prompt})
 
        try:
            token = self.credential.get_token("https://ai.azure.com/.default").token
 
            url = f"{self.endpoint}/chat/completions?api-version=2024-05-01-preview"
 
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
 
            body = {
                "model": self.model_name,
                "messages": self.history
            }
 
            response = requests.post(url, headers=headers, json=body, timeout=60)
            response.raise_for_status()
 
            data = response.json()
            assistant_message = data["choices"][0]["message"]["content"]
 
            self.history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
 
        except requests.exceptions.HTTPError as e:
            try:
                error_details = response.json()
            except Exception:
                error_details = response.text
            return f"Error communicating with Azure AI Foundry: {error_details}"
 
        except Exception as e:
            return f"Error communicating with Azure AI Foundry: {str(e)}"
 
    def clear_history(self):
        self.history = [
            {"role": "system", "content": CLIPPY_SYSTEM_MESSAGE}
        ]
 
 
@app.route('/')
def index():
    return render_template('index.html')
 
 
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
 
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
 
        if session_id not in chat_sessions:
            chat_sessions[session_id] = BouncingClippy()
 
        clippy = chat_sessions[session_id]
        response = clippy.send_message(user_message)
 
        return jsonify({
            'response': response,
            'session_id': session_id
        })
 
    except ValueError as e:
        print(f"Configuration error: {e}")
        return jsonify({'error': f'Configuration error: {str(e)}'}), 500
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
 
 
@app.route('/api/clear', methods=['POST'])
def clear():
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
 
        if session_id in chat_sessions:
            chat_sessions[session_id].clear_history()
 
        return jsonify({'success': True})
 
    except Exception as e:
        print(f"Error in clear endpoint: {e}")
        return jsonify({'error': f'An error occurred while clearing the chat: {str(e)}'}), 500
 
 
if __name__ == '__main__':
    if not os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT"):
        print("❌ Configuration Error:")
        print("Missing required environment variable:")
        print(" - AZURE_AI_FOUNDRY_ENDPOINT")
        exit(1)
 
    print("Starting BouncingClippy Web App...")
    print("Open your browser to: http://localhost:5000")
 
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
