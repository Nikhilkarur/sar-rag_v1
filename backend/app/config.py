from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:karur123@localhost:5432/aegis_db1"
    SECRET_KEY: str = "your-super-secret-jwt-key-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GROQ_API_KEY: str = "your-groq-api-key"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"

    # Database connection pool (tune per deployment; pool_size * workers
    # must stay below Postgres max_connections)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30      # seconds to wait for a free connection
    DB_POOL_RECYCLE: int = 1800    # recycle connections older than 30 min

    # Rate limiting
    RATE_LIMIT_INGEST_PER_MINUTE: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
