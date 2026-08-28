from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/results.db"
    admin_token: str = "change-me"
    cors_origins: str = "http://127.0.0.1:5500,http://localhost:5500"
    max_upload_mb: int = 50
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
