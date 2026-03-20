from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration from environment variables."""
    REDIS_URL: str = "redis://redis:6379/0"
    FAISS_DB_PATH: str = "./data/unified_vector_db"
    OPENAI_API_KEY: str  # Required from env
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    LLM_MODEL: str = "gpt-5-nano"
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
