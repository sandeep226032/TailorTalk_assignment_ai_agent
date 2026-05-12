# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     app_name: str = "TailorTalk Drive Agent"
#     app_version: str = "1.0.0"
#     environment: str = "development"
#     debug_mode: bool = True
#     allowed_origins: str | list[str] = ["*"]
#     groq_api_key: str
#     drive_folder_id: str
#     google_credentials_path: str = "credentials.json"
#     google_credentials_json: str | None = None
#     backend_url: str = "http://localhost:8000"
#     max_history_length: int = 20
#     llm_model: str = "llama-3.3-70b-versatile"
#     llm_temperature: float = 0.1

#     class Config:
#         env_file = ".env"

# # Singleton — imported everywhere, loaded once
# settings = Settings()/

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TailorTalk Drive Agent"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug_mode: bool = True

    allowed_origins: str | list[str] = ["*"]

    groq_api_key: str = Field(alias="GROQ_API_KEY")
    drive_folder_id: str = Field(alias="DRIVE_FOLDER_ID")

    google_credentials_path: str = Field(
        default="credentials.json",
        alias="GOOGLE_CREDENTIALS_PATH"
    )

    google_credentials_json: str | None = Field(
        default=None,
        alias="GOOGLE_CREDENTIALS_JSON"
    )

    backend_url: str = Field(
        default="http://localhost:8000",
        alias="BACKEND_URL"
    )

    max_history_length: int = 20
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()