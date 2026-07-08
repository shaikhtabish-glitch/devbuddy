"""
DevBuddy - OpenRouter LLM Client Factory

Uses LangChain's ChatOpenAI pointed at OpenRouter.
One client. Any model. Swap by changing a string.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load python/.env once, at import time, independent of the current working
# directory. Every module that needs the key imports this file, so this is the
# single place we read the environment (mirrors the Node.js config.js pattern).
# Without this, `python src/verification.py` fails with "OPENROUTER_API_KEY not
# set" even when a valid .env exists.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def get_llm(model: str | None = None, temperature: float = 0.0) -> ChatOpenAI:
    """
    Return a LangChain chat model pointed at OpenRouter.

    Args:
        model: OpenRouter model string (e.g. "openai/gpt-4o-mini", "anthropic/claude-sonnet").
               Defaults to DEFAULT_MODEL.
        temperature: 0.0 for deterministic, higher for creative.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not set.\n"
            "Copy .env.example to .env and add your key."
        )

    return ChatOpenAI(
        model=model or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE,
        api_key=api_key,
        temperature=temperature,
        default_headers={
            "HTTP-Referer": "https://github.com/your-org/devbuddy",
            "X-Title": "DevBuddy",
        },
    )
