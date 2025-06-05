import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")  # ❌ os not imported
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"

settings = Settings()