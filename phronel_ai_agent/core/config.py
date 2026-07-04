import os
from typing import Optional
from dotenv import load_dotenv
from .db import get_session
from .models import AgentConfig

import logging
logger = logging.getLogger("phronel")
# Load environment variables from .env if present
load_dotenv()

class ConfigManager:
    """Manages agent configuration with optional caching."""

    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        # 1. Try reading from SQLite Database first (Highest Priority for user runtime config)
        try:
            with get_session() as session:
                config = session.get(AgentConfig, key)
                if config is not None:
                    return config.value
        except Exception as e:
            # Handle cases where DB or tables are not initialized yet
            pass

        # 2. Fallback to environmental variables (PHRONEL_<KEY> as seed/default defaults)
        env_val = os.getenv(f"PHRONEL_{key.upper()}")
        if env_val is not None:
            try:
                ConfigManager.set(key, env_val, description=f"Loaded from environment variable PHRONEL_{key.upper()}")
            except Exception:
                pass
            return env_val

        # 3. Fallback to provided default value
        return default

    @staticmethod
    def set(key: str, value: str, description: Optional[str] = None):
        with get_session() as session:
            config = session.get(AgentConfig, key)
            if config:
                config.value = value
                if description:
                    config.description = description
            else:
                config = AgentConfig(key=key, value=value, description=description)
            session.add(config)
            session.commit()
            session.refresh(config)
        return config

config = ConfigManager()
