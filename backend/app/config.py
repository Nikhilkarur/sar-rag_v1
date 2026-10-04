from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Placeholder default only — the real connection string comes from backend/.env
    # (DATABASE_URL=...). Never commit a real password here.
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/aegis_db1"
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
    RATE_LIMIT_INGEST_PER_MINUTE: int = 120  # per tenant, counted after API-key auth
    # Pre-auth cap per client IP (IPv6: per /64) that sheds floods before the bcrypt key
    # check. Keep it above the tenant quota so a bank posting from one egress IP hits its
    # own quota first.
    RATE_LIMIT_INGEST_PER_IP_PER_MINUTE: int = 300

    # Ingestion hardening
    MAX_INGEST_PAYLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB hard cap

    # Composite risk at/above which an alert generates a SAR. Single source of truth —
    # referenced by the ingest pipeline, the portal simulator, and the RISK_SCORE_THRESHOLD
    # rule, so the filing threshold can never disagree across the codebase.
    SAR_RISK_THRESHOLD: int = 75

    # SAR generation resilience: if the LLM providers (Groq -> Gemini failover) both blip,
    # retry the whole generation a few times with linear backoff before marking the alert
    # PROCESSING_FAILED. A missed SAR is a regulatory gap, so we don't give up on the first error.
    SAR_GENERATION_MAX_ATTEMPTS: int = 3
    SAR_GENERATION_RETRY_BACKOFF_SECONDS: float = 2.0
    # SAR generations running at once for API ingests (the rest queue in PROCESSING). Each
    # holds a DB connection for the whole LLM call, so keep this well below
    # DB_POOL_SIZE + DB_MAX_OVERFLOW or an ingest burst starves requests of connections.
    SAR_GENERATION_CONCURRENCY: int = 4
    # On startup, alerts a previous worker left in PROCESSING are marked PROCESSING_FAILED
    # once they are this old (longer than a worst-case generation with all retries).
    STUCK_PROCESSING_TIMEOUT_MINUTES: int = 15

    # SAR workflow: when False (current), a generated SAR waits for a human compliance officer
    # to review and approve it in the Aegis dashboard BEFORE it is finalized + delivered to the
    # bank — an explicit human-in-the-loop on the Aegis side. When True, the SAR auto-finalizes
    # and delivers immediately, leaving the file-with-FIU decision to the bank's own admin.
    AUTO_APPROVE_SARS: bool = False

    # PII encryption at rest (Fernet). MUST be set explicitly in production;
    # when empty, a key is derived from SECRET_KEY so dev works out of the box.
    PII_ENCRYPTION_KEY: str = ""

    # --- LLM provider for SAR generation ---
    # Primary provider ("groq" | "gemini"); if a call fails (e.g. a free-tier rate/token
    # cap), generation automatically retries on LLM_FALLBACK_PROVIDER. The pipeline is
    # otherwise provider-agnostic.
    LLM_PROVIDER: str = "groq"
    LLM_FALLBACK_PROVIDER: str = ""     # e.g. "gemini"; empty = no fallback
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # --- Paid drafting tier (PLACEHOLDER / not live) ---
    # Scaffolding for future plan-based model selection (see app/services/model_router.py).
    # Today the whole platform runs on the FREE tier (Groq -> Gemini above). Paid plans would
    # draft on Anthropic (Opus/Sonnet); the key is intentionally EMPTY until we enable paid
    # inference. When set, the router routes PRO-tier tenants here — no other code changes.
    ANTHROPIC_API_KEY: str = ""                       # empty = paid tier not enabled
    PRO_MODEL: str = "claude-opus-4-8"                # Premium drafting (highest quality)
    PRO_MODEL_STANDARD: str = "claude-sonnet-4-6"     # mid paid tier (Sonnet), if offered

    # --- RAG / embeddings ---
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_PROVIDER: str = "local"               # "local" (bge) | "openai"
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    OPENAI_API_KEY: str = ""                         # only for the "openai" provider
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    RAG_TOP_K_CHUNKS: int = 8
    MAX_UPLOAD_FILE_SIZE_MB: int = 50
    # Caps on the policy PDF's CONTENT (not just its bytes): parsing, tokenizing and
    # embedding cost scales with pages/text, and an oversize policy would pin a CPU for
    # minutes. Uploads over either cap are rejected with 413.
    MAX_POLICY_PAGES: int = 500
    MAX_POLICY_TEXT_CHARS: int = 1_000_000

    # Public base URL of this API (used to build the SAR pdf_url in webhooks).
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Comped tenants: comma-separated PUBLIC tenant ids (e.g. "TEN-0005") that are billed
    # Rs.0 and pinned to the free drafting plan. Empty = nobody. Public ids are handed out
    # sequentially at approval, so this must be set per deployment, never hard-coded.
    COMPED_TENANT_IDS: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Values that MUST be overridden before this is a real deployment. Used by the
    # production fail-closed check below.
    _DEFAULT_SECRET_KEY = "your-super-secret-jwt-key-min-32-chars"

    @property
    def comped_tenant_ids(self) -> frozenset[str]:
        return frozenset(t.strip().upper() for t in self.COMPED_TENANT_IDS.split(",") if t.strip())

    def production_config_errors(self) -> list[str]:
        """Fatal misconfigurations for a production boot. Empty list = OK.

        We fail closed rather than trust that ENVIRONMENT-gated protections (SSRF
        guard, docs hiding) plus at-rest encryption were all wired up by hand: if
        the encryption key or JWT secret are still defaults in production, the
        'encryption at rest' is derivable from a known key and provides no real
        protection, so refuse to start."""
        errors: list[str] = []
        if self.ENVIRONMENT == "production":
            if not self.PII_ENCRYPTION_KEY:
                errors.append(
                    "PII_ENCRYPTION_KEY must be set in production — without it the "
                    "at-rest PII key is derived from SECRET_KEY and offers no real protection."
                )
            else:
                # A malformed key would otherwise boot fine and only fail on the first
                # encrypt (ingest, approval, key reveal) with a 500.
                from cryptography.fernet import Fernet
                try:
                    Fernet(self.PII_ENCRYPTION_KEY.encode("utf-8"))
                except Exception:
                    errors.append(
                        "PII_ENCRYPTION_KEY is not a valid Fernet key (32 url-safe base64-encoded "
                        "bytes); generate one with cryptography.fernet.Fernet.generate_key()."
                    )
            if self.SECRET_KEY == self._DEFAULT_SECRET_KEY:
                errors.append("SECRET_KEY must be overridden from its built-in default in production.")
        return errors

settings = Settings()
