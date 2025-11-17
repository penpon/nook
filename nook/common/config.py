from pydantic import ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings


class BaseConfig(BaseSettings):
    """基本設定クラス"""

    # API関連
    OPENAI_API_KEY: SecretStr
    REDDIT_CLIENT_ID: SecretStr | None = None
    REDDIT_CLIENT_SECRET: SecretStr | None = None

    # ログ関連
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # リクエスト関連
    REQUEST_TIMEOUT: int = Field(default=30, ge=1, le=300)
    REQUEST_DELAY: float = Field(default=1.0, ge=0.1, le=10.0)
    MAX_RETRIES: int = Field(default=3, ge=1, le=10)

    # データ保存関連
    DATA_DIR: str = Field(default="data")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # 余分な環境変数を無視
    )


class RedditConfig(BaseConfig):
    """Reddit用の設定"""

    REDDIT_USER_AGENT: str = Field(default="NookBot/1.0 by YourUsername")


class ServiceConfig(BaseConfig):
    """各サービス用の設定基底クラス"""

    SERVICE_ENABLED: bool = Field(default=True)
    COLLECTION_INTERVAL: int = Field(default=3600)  # 秒単位
