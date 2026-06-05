"""
Configuration Module

Handles configuration for the AI Browser.
Loads settings from config/config.yaml, .env, and environment variables.
Priority: environment variables > .env > config.yaml > defaults.
"""

import os
from typing import Optional
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ── Defaults ────────────────────────────────────────────────
_DEFAULTS = {
    "ai_provider": "openai",
    "ai_model": "gpt-4",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "api_base_url": "",
    "headless_mode": True,
    "browser_slow_mo": 0,
    "viewport_width": 1280,
    "viewport_height": 900,
    "max_steps": 15,
    "task_timeout": 300,
    "max_retries": 3,
    "vision_mode": False,
    "memory_db_path": "memory.db",
}

# ── YAML Loader ─────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"


def _load_yaml() -> dict:
    """Load configuration from config.yaml if available."""
    if not HAS_YAML:
        return {}
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _env(key: str, fallback=None):
    """Read an environment variable (case-insensitive key)."""
    return os.getenv(key.upper(), fallback)


def _resolve(key: str, yaml_cfg: dict):
    """Resolve a setting: env > yaml > default."""
    env_val = _env(key)
    if env_val is not None:
        return env_val
    if key in yaml_cfg and yaml_cfg[key] not in (None, ""):
        return yaml_cfg[key]
    return _DEFAULTS.get(key)


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ── Build Config ────────────────────────────────────────────
_yaml_cfg = _load_yaml()


class Config:
    """Configuration class.

    Settings are resolved at import time in this order of precedence:
    environment variable  >  config.yaml  >  built-in default.
    """

    # AI Provider Settings
    AI_PROVIDER: str = str(_resolve("ai_provider", _yaml_cfg))
    AI_MODEL: str = str(_resolve("ai_model", _yaml_cfg))
    OPENAI_API_KEY: Optional[str] = _resolve("openai_api_key", _yaml_cfg) or None
    ANTHROPIC_API_KEY: Optional[str] = _resolve("anthropic_api_key", _yaml_cfg) or None

    # Custom API endpoint (for local / self-hosted models)
    API_BASE_URL: Optional[str] = _resolve("api_base_url", _yaml_cfg) or None

    # Browser Settings
    HEADLESS_MODE: bool = _to_bool(_resolve("headless_mode", _yaml_cfg))
    BROWSER_SLOW_MO: int = _to_int(_resolve("browser_slow_mo", _yaml_cfg))
    VIEWPORT_WIDTH: int = _to_int(_resolve("viewport_width", _yaml_cfg), 1280)
    VIEWPORT_HEIGHT: int = _to_int(_resolve("viewport_height", _yaml_cfg), 900)

    # Memory Settings
    MEMORY_DB_PATH: str = str(_resolve("memory_db_path", _yaml_cfg))

    # Execution Settings
    MAX_STEPS: int = _to_int(_resolve("max_steps", _yaml_cfg), 15)
    TASK_TIMEOUT: int = _to_int(_resolve("task_timeout", _yaml_cfg), 300)
    MAX_RETRIES: int = _to_int(_resolve("max_retries", _yaml_cfg), 3)

    # Vision Settings
    VISION_MODE: bool = _to_bool(_resolve("vision_mode", _yaml_cfg))

    @classmethod
    def validate(cls):
        """Validate configuration.

        API keys are only required when using a cloud provider *without*
        a custom base URL (local models usually don't need a key).
        """
        using_local = bool(cls.API_BASE_URL)
        if not using_local:
            if cls.AI_PROVIDER.lower() == "openai" and not cls.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY not set.  Set it in .env, config.yaml, "
                    "or as an environment variable.  If you are using a local "
                    "model, set API_BASE_URL instead."
                )
            if cls.AI_PROVIDER.lower() == "anthropic" and not cls.ANTHROPIC_API_KEY:
                raise ValueError(
                    "ANTHROPIC_API_KEY not set.  Set it in .env, config.yaml, "
                    "or as an environment variable."
                )

    @classmethod
    def to_dict(cls):
        """Convert config to dictionary."""
        return {
            "ai_provider": cls.AI_PROVIDER,
            "ai_model": cls.AI_MODEL,
            "api_base_url": cls.API_BASE_URL,
            "headless_mode": cls.HEADLESS_MODE,
            "browser_slow_mo": cls.BROWSER_SLOW_MO,
            "viewport_width": cls.VIEWPORT_WIDTH,
            "viewport_height": cls.VIEWPORT_HEIGHT,
            "memory_db_path": cls.MEMORY_DB_PATH,
            "max_steps": cls.MAX_STEPS,
            "task_timeout": cls.TASK_TIMEOUT,
            "max_retries": cls.MAX_RETRIES,
            "vision_mode": cls.VISION_MODE,
        }
