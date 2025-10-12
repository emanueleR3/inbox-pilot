# api/v1/src/core/config.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()  # Carica le variabili d'ambiente dal file .env

class Settings(BaseSettings):
    PROJECT_NAME: str = "Corretto MVP2"
    ENV: str = "development"
    PORT: int = 8000
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI")
    PUBSUB_TOPIC_PATH: str = os.getenv("GOOGLE_PUBSUB_TOPIC_PATH")
    PUBSUB_SUBSCRIPTION_PATH: str = os.getenv("GOOGLE_PUBSUB_SUBSCRIPTION_PATH")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")

    class Config:
        env_file = ".env"

settings = Settings()