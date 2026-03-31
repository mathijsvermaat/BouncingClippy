import asyncio
import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from azure.identity import ManagedIdentityCredential
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory

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
        self.deployment_name = os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o")

        if not self.endpoint:
            raise ValueError(
                "Missing required environment variable: AZURE_AI_FOUNDRY_ENDPOINT"
            )

        credential = ManagedIdentityCredential()

        self.chat_service = AzureChatCompletion(
            endpoint=self.endpoint,
            deployment_name=self.deployment_name,
            credential=credential,
        )

        self.settings = AzureChatPromptExecutionSettings()
        self.chat_history = ChatHistory()
        self.chat_history.add_system_message(CLIPPY_SYSTEM_MESSAGE)

    async def send_message_async(self, user_prompt: str) -> str:
        self.chat_history.add_user_message(user_prompt)
        try:
            response = await self.chat_service.get_chat_message_content(
                chat_history=self.chat_history,
                settings=self.settings
            )
            assistant_message = str(response)
            self.chat_history.add_assistant_message(assistant_message)
            return assistant_message
        except Exception as e:
            return f"Error communicating with Azure AI Foundry: {str(e)}"

    def clear_history(self):
        self.chat_history.clear()
        self.chat_history.add_system_message(CLIPPY_SYSTEM_MESSAGE)


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
        response = asyncio.run(clippy.send_message_async(user_message))

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