from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "geopolitical_risk"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    
    MONGODB_HOST: str = "localhost"
    MONGODB_PORT: int = 27017
    MONGODB_DB: str = "geopolitical_risk"
    
    # World Bank
    WORLD_BANK_BASE_URL: str = "https://api.worldbank.org/v2"
    
    # Phase 2: AI Explanations (Optional)
    GEMINI_API_KEY: str = ""
    
    # System
    LOG_LEVEL: str = "INFO"
    INDIA_COUNTRY_CODE: str = "IND"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def mongodb_url(self) -> str:
        """Get MongoDB connection URL"""
        return f"mongodb://{self.MONGODB_HOST}:{self.MONGODB_PORT}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
