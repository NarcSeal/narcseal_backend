import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/narcseal_db"
    )
    
    # JWT Configuration
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "your-ultra-secret-key-change-this-in-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480 # 8-hour shift

settings = Settings()
