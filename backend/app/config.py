from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:karur123@localhost:5432/aegis_db1"
    SECRET_KEY: str = "your-super-secret-jwt-key-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GROQ_API_KEY: str = "your-groq-api-key"
    ENVIRONMENT: str = "development"
    # 5173 = Aegis dashboard; 5174/3000 = mock bank UI origins (browser CORS)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    # Database connection pool (tune per deployment; pool_size * workers
    # must stay below Postgres max_connections)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30      # seconds to wait for a free connection
    DB_POOL_RECYCLE: int = 1800    # recycle connections older than 30 min

    # Rate limiting
    RATE_LIMIT_INGEST_PER_MINUTE: int = 120

    # Ingestion hardening
    MAX_INGEST_PAYLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB hard cap

    # PII encryption at rest (Fernet). MUST be set explicitly in production;
    # when empty, a key is derived from SECRET_KEY so dev works out of the box.
    PII_ENCRYPTION_KEY: str = ""

    # --- RAG / embeddings ---
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_PROVIDER: str = "local"               # "local" (bge) | "openai"
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    OPENAI_API_KEY: str = ""                         # only for the "openai" provider
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    RAG_TOP_K_CHUNKS: int = 8
    MAX_UPLOAD_FILE_SIZE_MB: int = 50

    # Public base URL of this API (used to build the SAR pdf_url in webhooks).
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
