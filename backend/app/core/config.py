"""Application configuration and environment handling.

This module uses Pydantic's BaseSettings to load configuration from
environment variables. A single instance of ``Settings`` should be
created at application start and reused via dependency injection.

The values defined here are intentionally conservative defaults
appropriate for local development. Production deployments should
override these via environment variables or a ``.env`` file.

Important: All secrets such as database passwords or JWT keys are
expected to come from the environment and must never be hard coded.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Fields:
        env: The running environment (e.g. ``development``, ``production``).
        database_url: The SQLAlchemy database URL.
        redis_url: The Redis connection URL used for Celery.
        minio_endpoint: The address of the MinIO/S3 service.
        minio_access_key: Access key for MinIO.
        minio_secret_key: Secret key for MinIO.
        jwt_secret_key: Secret key used to sign JWT tokens.
        jwt_algorithm: Algorithm used for JWT encoding/decoding.
        jwt_access_token_expire_minutes: Minutes before JWT access tokens expire.
        smtp_host: SMTP server host (MailHog in local setup).
        smtp_port: SMTP server port.
        smtp_user: SMTP username (unused for MailHog).
        smtp_password: SMTP password (unused for MailHog).
        mail_from: Default ``from`` email address.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg2://krishva:krishva@db:5432/vehicle_analytics",
        alias="DATABASE_URL",
    )

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/0", alias="CELERY_RESULT_BACKEND")

    # App
    ENV: str = Field(default="development")
    APP_NAME: str = Field(default="cctv-vehicle-analytics")
    API_V1_STR: str = Field(default="/api")

    # Security / Auth
    SECRET_KEY: str = Field(default="change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)

    # Database / Redis
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@db:5432/vehicle_analytics"
    )
    REDIS_URL: str = Field(default="redis://redis:6379/0")

    # MinIO
    MINIO_ENDPOINT: str = Field(default="minio:9000")
    MINIO_ACCESS_KEY: str = Field(default="minio")
    MINIO_SECRET_KEY: str = Field(default="minio123")
    MINIO_BUCKET: str = Field(default="events")
    MINIO_SECURE: bool = Field(default=False)

    # Models
    YOLO_MODEL_PATH: str = Field(default="/models/yolov8n.onnx")
    PLATE_MODEL_PATH: str = Field(default="/models/plate.onnx")
    PLATE_CONF: float = Field(default=0.35)

    # Material/load models (optional ONNX)
    MATERIAL_MODEL_PATH: str | None = Field(default=None)
    LOAD_MODEL_PATH: str | None = Field(default=None)

    # Identification: ANPR | BARCODE | BOTH
    IDENT_MODE: str = Field(default="ANPR")

    DETECTION_BACKEND: str = Field(default="local")  # local|jetson

    # CORS / security
    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    # Notifications (Twilio / FCM optional)
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None
    NOTIFY_SMS_TO: str | None = None
    FCM_SERVER_KEY: str | None = None
    FCM_ENDPOINT: str = Field(default="https://fcm.googleapis.com/fcm/send")
    NOTIFY_DEBOUNCE_SECONDS: int = Field(default=5, description="Minimum seconds between notifications per gate/channel")

    # Mailhog / SMTP
    SMTP_HOST: str = Field(default="mailhog")
    SMTP_PORT: int = Field(default=1025)
    SMTP_FROM: str = Field(default="no-reply@local.test")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings object.

    Using a cached settings instance ensures that environment variables
    are only read once and consistent across the application lifetime.
    """

    return Settings()
