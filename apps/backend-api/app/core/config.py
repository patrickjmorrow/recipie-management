from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://recipie:recipie@localhost:5432/recipie"
    ENVIRONMENT: str = "local"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_PUBLIC_URL: str = ""  # public-facing base URL for presigned URLs; defaults to S3_ENDPOINT_URL
    S3_BUCKET_NAME: str = "recipie"
    S3_ACCESS_KEY: str = "rustfsadmin"
    S3_SECRET_KEY: str = "rustfsadmin"

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    GOOGLE_CLIENT_ID: str = ""
    JWT_SECRET_KEY: str = "changeme"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440


settings = Settings()
