import os
from dotenv import load_dotenv

load_dotenv()
# Ensure GOOGLE_API_KEY is set if GEMINI_API_KEY is present for better compatibility with litellm/google-sdk
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    LM_STUDIO_API_BASE = os.getenv("LM_STUDIO_API_BASE", "http://localhost:1234/v1")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
