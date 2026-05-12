from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "TailorTalk Drive Agent"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug_mode: bool = True
    allowed_origins: str | list[str] = ["*"]
    groq_api_key: str
    drive_folder_id: str
    google_credentials_path: str = "credentials.json"
    backend_url: str = "http://localhost:8000"
    max_history_length: int = 20
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1

    class Config:
        env_file = ".env"

# Singleton — imported everywhere, loaded once
settings = Settings()