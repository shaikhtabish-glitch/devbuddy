"""
DevBuddy — Central Configuration

Loads .env once. Every module imports from here.
Single source of truth for all config values.
"""
import os
from dotenv import load_dotenv

# Load .env from the repo root (build/python/) regardless of CWD
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_ENV_PATH)

# ─── OpenRouter ──────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# ─── Model ───────────────────────────────────────────────────
DEVBUDDY_MODEL = os.environ.get("DEVBUDDY_MODEL", "openai/gpt-4o-mini")
DEVBUDDY_MODEL_ALT = os.environ.get("DEVBUDDY_MODEL_ALT")  # optional, for swap tests


def validate() -> None:
    """Raise ValueError if required config is missing. Callers invoke this explicitly."""
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY not set.\n"
            "Copy .env.example to .env and add your key."
        )
