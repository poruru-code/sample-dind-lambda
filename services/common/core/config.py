"""
Common Configuration
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class BaseAppConfig(BaseSettings):
    """
    アプリケーション共通設定
    """

    LOG_LEVEL: str = Field(default="INFO", description="ログレベル")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )
