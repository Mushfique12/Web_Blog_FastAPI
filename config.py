from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Settings class for application configuration
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Settings for JWT Authentication
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Settings for file uploads
    max_upload_size_bytes: int = 5 * 1024 * 1024  # 5 MB

    # Default no. of pages to be displayed
    posts_per_page: int = 5

    # Settings for password reset token expiration
    reset_token_expire_minutes: int = 60

    # Settings for email server configuration
    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True

    # Settings for frontend URL
    frontend_url: str = "http://localhost:8000"


# Loaded from .env file
settings = Settings()   # type: ignore[call-arg]