from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str
    DB_NAME: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str = ""
    RETELL_WEBHOOK_SECRET: str = ""
    RETELL_AGENT_ID_LISA: str = ""
    RETELL_AGENT_ID_BOB: str = ""
    BACKEND_URL: str = ""  # Backend public URL (used for Retell webhooks)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    RETELL_API_KEY: str = ""
    BASE_URL: str = "http://localhost:8000"
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    PROFILE_IMAGE_MAX_BYTES: int = 2_000_000

    # Vector store / embedding settings (added in Prompt 2)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_COLLECTION_NAME: str = "job_jds"
    ENABLE_VECTOR_BOOTSTRAP: bool = False
    ENABLE_EMBEDDING_SCORING: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
