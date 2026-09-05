from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "RecoverAI"
    database_url: str = "sqlite:///./data/recoverai.db"
    jwt_secret: str = "change-this-demo-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    admin_username: str = "admin@recoverai.demo"
    admin_password: str = "RecoverAI@2026"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    gemini_api_key: str | None = None
    razorpay_mode: str = "simulator"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self): return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings(): return Settings()

