import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError
from core.exceptions import ConfigurationError

class Settings(BaseSettings):
    """Strict configuration model based on environment variables."""
    NOTION_API_KEY: str
    OPENAI_API_KEY: str
    
    # Optional Configurations with defaults
    NOTION_MAX_DEPTH: int = 3
    NOTION_ROOT_PAGE_ID: str = ""
    NOTION_MD_PATH: str = "workspace_context.md"
    NOTION_JSON_PATH: str = "workspace_fragments.json"
    NOTION_SEARCH_TOP_K: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def load_config() -> Settings:
    """Loads and validates the configuration, failing fast if missing."""
    try:
        return Settings()
    except ValidationError as e:
        # Extract clear messages for the missing variables
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        error_msg = " | ".join(errors)
        raise ConfigurationError(f"Missing or invalid environment variables -> {error_msg}")
    except Exception as e:
        raise ConfigurationError(f"Failed to load environment configuration: {e}")

# We intentionally do not instantiate it here globally to avoid failing import if .env is missing during test discovery
# But we can provide a getter
_settings_instance = None

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = load_config()
    return _settings_instance
