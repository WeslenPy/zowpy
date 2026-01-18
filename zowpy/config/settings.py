"""
Settings - Configuração via Pydantic Settings.

Lê de .env e variáveis de ambiente.
"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuração do ZowPy"""
    
    # Database
    zowpy_db_url: str = "sqlite+aiosqlite:///zowpy.db"
    
    # Account Path
    zowpy_account_path: str = "./accounts"
    
    # Default Device Environment
    zowpy_default_device_env: str = "android"
    
    # Logging
    zowpy_log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global
settings = Settings()








