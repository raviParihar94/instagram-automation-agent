"""
Typed configuration loader/saver.

Every user of this app configures their OWN local config.json (mounted as a
Docker volume so it survives container restarts). Nothing here is shared
between users — this is a self-hosted, single-tenant-per-instance design.
"""
import json
import os
from typing import List
from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


class Config(BaseModel):
    access_token: str = ""
    ig_user_id: str = ""
    niche: str = "General"
    system_prompt: str = "Create engaging, SEO-friendly Instagram content."
    content_type: str = Field(default="meme", description="meme | health_tip | news | custom")
    posts_per_day: int = 1
    post_times: List[str] = Field(default_factory=lambda: ["12:00"])
    hashtag_count: int = 10
    search_keywords: str = ""
    auto_post: bool = False


class Settings:
    """Reads/writes the JSON config file used by both the dashboard and the scheduler."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = config_path

    def load_config(self) -> Config:
        if not os.path.exists(self.config_path):
            cfg = Config()
            self.save_config(cfg)
            return cfg
        with open(self.config_path, "r") as f:
            data = json.load(f)
        return Config(**data)

    def save_config(self, config: Config) -> None:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config.model_dump(), f, indent=4)
