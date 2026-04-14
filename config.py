from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str
    DB_NAME: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = ""
    RETELL_API_KEY: str = ""
    RETELL_WEBHOOK_SECRET: str = ""
    RETELL_AGENT_ID_LISA: str = ""
    RETELL_AGENT_ID_BOB: str = ""
    BACKEND_URL: str = ""  # Backend public URL (used for Retell webhooks)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
