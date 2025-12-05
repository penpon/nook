from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """基本設定クラス"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # API関連
    OPENAI_API_KEY: SecretStr = Field(validation_alias="OPENAI_API_KEY")
    REDDIT_CLIENT_ID: SecretStr | None = Field(
        default=None, validation_alias="REDDIT_CLIENT_ID"
    )
    REDDIT_CLIENT_SECRET: SecretStr | None = Field(
        default=None, validation_alias="REDDIT_CLIENT_SECRET"
    )

    # ログ関連
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        validation_alias="LOG_FORMAT",
    )

    # リクエスト関連
    REQUEST_TIMEOUT: int = Field(
        default=30, ge=1, le=300, validation_alias="REQUEST_TIMEOUT"
    )
    REQUEST_DELAY: float = Field(
        default=1.0, ge=0.1, le=10.0, validation_alias="REQUEST_DELAY"
    )
    MAX_RETRIES: int = Field(default=3, ge=1, le=10, validation_alias="MAX_RETRIES")

    # データ保存関連
    DATA_DIR: str = Field(default="data", validation_alias="DATA_DIR")


class RedditConfig(BaseConfig):
    """Reddit用の設定"""

    REDDIT_USER_AGENT: str = Field(default="NookBot/1.0 by YourUsername")


class ServiceConfig(BaseConfig):
    """各サービス用の設定基底クラス"""

    SERVICE_ENABLED: bool = Field(default=True)
    COLLECTION_INTERVAL: int = Field(default=3600)  # 秒単位
