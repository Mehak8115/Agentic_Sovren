# agents/groq_client.py
"""
Shared Groq client with automatic model fallback on rate limit.
All agents import `groq_chat` from here instead of calling _groq directly.
"""

import os
from groq import Groq, RateLimitError
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Models tried in order — fastest/best first, fallbacks after
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


def groq_chat(messages: list[dict], temperature: float = 0, **kwargs) -> str:
    """
    Call Groq chat with automatic model fallback on RateLimitError.
    Returns the response content string directly.
    Raises RateLimitError only if ALL models are exhausted.
    """
    last_error = None
    for model in FALLBACK_MODELS:
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            if model != FALLBACK_MODELS[0]:
                print(f"[groq_client] Using fallback model: {model}")
            return resp.choices[0].message.content.strip()
        except RateLimitError as e:
            print(f"[groq_client] Rate limit on '{model}', trying next...")
            last_error = e

    raise RateLimitError(
        message="All Groq models are rate-limited. Please wait and try again.",
        response=last_error.response,
        body=last_error.body,
    )
