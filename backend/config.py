from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    OLLAMA_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "llama3.2:3b"
    EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    STORAGE_DIR: Path = Path("storage/sessions")
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 120
    RETRIEVAL_TOP_K: int = 12
    RERANK_TOP_N: int = 5
    GUEST_TTL_HOURS: int = 24
    CORS_ORIGINS: str = "http://localhost:8501"
    MAX_UPLOAD_MB: int = 20
    MAX_DATASET_ROWS: int = 100000
    MAX_DATASET_COLUMNS: int = 200
    MAX_XLSX_SHEETS: int = 10
    MAX_UNPACKED_MB: int = 100
    GUEST_MAX_WORKSPACES: int = 2
    GUEST_MAX_UPLOADS: int = 10
    WORKSPACE_MAX_UPLOADS: int = 100
    GUEST_MAX_REQUESTS: int = 100
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    PUBLIC_API_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:8501"
    JOB_LEASE_SECONDS: int = 600

    @property
    def cors_origins(self):
        return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]

settings = Settings()
if len(settings.JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")
