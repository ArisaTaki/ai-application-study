import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-5-nano-2025-08-07")
        self.api_base_url = os.getenv("OPENAI_BASE_URL")
        self.langchain_available = (os.getenv("LANGCHAIN_AVAILABLE", "true").lower() == "true")