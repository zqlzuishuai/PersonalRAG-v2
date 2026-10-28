from config import Settings
from langchain.chat_models import BaseChatModel
def ask_question(
        settings: Settings, 
        user_id: str,
        conversation_id: str, 
        query: str, 
        clinet_request_id: str,
        chat_model: BaseChatModel
        ):
    """111"""
    