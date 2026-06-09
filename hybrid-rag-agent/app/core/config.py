"""
app/core/config.py — 集中環境設定
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env（專案根目錄）
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)


class Settings:
    # --- LLM (LiteLLMOpenAI) ---
    LLM_MODEL: str = os.getenv("LLM_MODEL", "TXC-LLM")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://192.168.37.71:32290")

    # --- PostgreSQL ---
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "hybrid_rag")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Agent Session DB (Agno 歷史持久化) ---
    AGENT_DB_URL: str = os.getenv(
        "AGENT_DB_URL",
        "postgresql://webui:webui@postgresql.database.svc.cluster.local:5432/meeting_records",
    )
    AGENT_SESSION_TABLE: str = os.getenv("AGENT_SESSION_TABLE", "agent_sessions_hybridRAG")
    AGENT_DB_SCHEMA: str = os.getenv("AGENT_DB_SCHEMA", "ai")

    # --- Qdrant ---
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "docs")

    # --- Embedding (OpenAI-compatible, e.g. BAAI/bge-m3 via vLLM) ---
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "http://192.168.37.71:30806/v1")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "1111")

    # --- Reranker (BAAI/bge-reranker-v2-m3 via vLLM) ---
    RERANKER_BASE_URL: str = os.getenv("RERANKER_BASE_URL", "http://192.168.37.71:30807")
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    RERANKER_TOP_N: int = int(os.getenv("RERANKER_TOP_N", "5"))


settings = Settings()
