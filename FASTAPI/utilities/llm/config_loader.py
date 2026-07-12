import os
import yaml
from dotenv import load_dotenv

# utilities/llm/ -> FASTAPI/
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(_BASE, "config.yaml")
_ENV_PATH = os.path.join(_BASE, "utilities", ".env")

_cache = None


def get_llm_config():
    """Load and return the `llm` section of config.yaml.

    Fails loudly (no silent fallback) if config.yaml is missing. API keys are
    read from the utilities/.env via python-dotenv; litellm picks them up from
    the process environment (GOOGLE_API_KEY, HUGGINGFACE_API_KEY).
    """
    global _cache
    if _cache is None:
        if not os.path.exists(CONFIG_PATH):
            raise RuntimeError(
                f"config.yaml not found at {CONFIG_PATH}. "
                "Copy config.example.yaml to config.yaml and set your model."
            )
        load_dotenv(dotenv_path=_ENV_PATH)
        with open(CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
        if "llm" not in data:
            raise RuntimeError("config.yaml is missing the top-level 'llm' section.")
        _cache = data["llm"]
    return _cache
