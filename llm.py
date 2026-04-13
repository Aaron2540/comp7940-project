import logging

from openai import OpenAI

import config

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
    return _client


def chat(history: list[dict], user_message: str) -> str:
    """Send message to LLM with conversation history, return the reply."""
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = get_client().chat.completions.create(
            model=config.LLM_MODEL, messages=messages,
            max_tokens=1024, temperature=0.7,
        )
        reply = resp.choices[0].message.content.strip()
        tokens = resp.usage.total_tokens if resp.usage else "N/A"
        logger.info("LLM response: model=%s, tokens=%s", config.LLM_MODEL, tokens)
        return reply
    except Exception as e:
        logger.exception("LLM API call failed")
        return f"Sorry, I encountered an error: {e}"
