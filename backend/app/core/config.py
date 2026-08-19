from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KMRL Document Intelligence & Action Portal"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = "postgresql+asyncpg://kmrl:kmrl@localhost:5432/kmrl_portal"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    jwt_secret: str = "replace-this-demo-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    storage_path: str = "./storage"
    object_storage_endpoint: str | None = None
    object_storage_bucket: str = "kmrl-demo"
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None
    openai_api_key: str | None = None
    openai_api_base: str | None = None
    max_upload_size_mb: int = 25
    low_ocr_confidence_threshold: float = 0.70
    demo_purge_after_judging: bool = False
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    rag_generation_provider: str = "openai"
    rag_generation_model: str = "gpt-4o-mini"
    rag_vector_top_k: int = 15
    rag_keyword_top_k: int = 15
    rag_final_top_k: int = 4
    rag_min_relevance: float = 0.18
    rag_min_rerank_score: float = 0.20
    rag_document_scope_default: str = "document"
    rag_low_ocr_penalty: float = 0.18
    rag_diagnostics_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
