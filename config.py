import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# the system prompt tells the LLM what role it plays
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a Campus Assistant chatbot for university students. "
    "You help with: 1) Course information and academic questions, "
    "2) Campus life, events, and activities, "
    "3) Study tips and learning resources, "
    "4) Scheduling and time management. "
    "Be friendly, concise, and helpful. "
    "If asked about events, suggest /events. "
    "If asked about study partners, suggest /profile and /match. "
    "If asked about tasks, suggest /add and /list. "
    "Always respond in the same language the user uses."
)

MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))
