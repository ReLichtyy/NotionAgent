from typing import List, Dict, Any
from openai import OpenAI, OpenAIError
from core.config import get_settings
from core.exceptions import OpenAIConnectionError
from core.logger import get_logger

logger = get_logger("OpenAIClient")

class OpenAIAppClient:
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = "gpt-4o-mini"
        
    def test_connection(self) -> bool:
        """
        Tests the connection by listing models or making a very small dummy request.
        """
        try:
            self.client.models.list()
            logger.info("Successfully connected to OpenAI API.")
            return True
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise OpenAIConnectionError(f"Failed to connect to OpenAI: {e}")
        except Exception as e:
            logger.error(f"Unexpected error when connecting to OpenAI: {e}")
            raise OpenAIConnectionError(f"Unexpected error: {e}")

    def chat(self, messages: List[Dict[str, str]], model: str = None, tools: List[Dict[str, Any]] = None) -> Any:
        """
        Sends a conversation to OpenAI and returns the assistant's message object.
        """
        target_model = model or self.default_model
        try:
            kwargs = {
                "model": target_model,
                "messages": messages,
                "temperature": 0.7
            }
            if tools:
                kwargs["tools"] = tools
                
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message
        except OpenAIError as e:
            logger.error(f"Chat completion failed: {e}")
            return None
