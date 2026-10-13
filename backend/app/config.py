from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Security & JWT
    SECRET_KEY: str = "tournament_secret_key_at_least_32_characters_for_hs256_security_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    # Default is SQLite for quick local startup without an external DB server.
    # Production uses PostgreSQL: postgresql+psycopg://user:password@localhost:5432/tournament_db
    DATABASE_URL: str = "sqlite:///./tournament.db"

    # Environment & CORS
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
