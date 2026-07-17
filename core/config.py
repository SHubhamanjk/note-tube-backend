from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr

class Settings(BaseSettings):
    PROJECT_NAME: str = "Note-Tube Backend"
    ENVIRONMENT: str = "prod"
    
    # Database
    MONGO_URI: str
    
    # Security
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 60 # 60 days
    
    # Email / SMTP
    SMTP_FROM_EMAIL: EmailStr
    SMTP_FROM_NAME: str = "Medha.ai"
    GMAIL_APP_PASSWORD: str
    
    # Groq API
    GROQ_API_KEY: str
    GROQ_REWRITE_MODEL: str = "llama3-70b-8192"
    GROQ_STT_MODEL: str = "whisper-large-v3"
    
    # Gemini API
    GEMINI_API_KEY: str
    GEMINI_CHAT_MODEL: str = "gemini-1.5-flash"
    
    # Google Cloud Storage
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GCS_BUCKET_NAME: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
