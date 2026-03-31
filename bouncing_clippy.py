import asyncio
import os
from dotenv import load_dotenv
from azure.identity import ManagedIdentityCredential
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory

load_dotenv()

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

    def add_system_message(self, content: str):
        self.chat_history.add_system_message(content)

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
            error_msg = f"Error communicating with Azure AI Foundry: {str(e)}"
            print(f"\n❌ {error_msg}")
            return error_msg

    def send_message(self, user_prompt: str) -> str:
        return asyncio.run(self.send_message_async(user_prompt))

    def clear_history(self):
        self.chat_history.clear()