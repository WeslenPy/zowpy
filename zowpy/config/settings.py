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
    
    # Default Device Environment
    zowpy_default_device_env: str = "android"

    zowpy_db_echo:bool = False
    zowpy_db_pool_size:int = 10
    zowpy_db_max_overflow:int = 20
    zowpy_db_pool_recycle:int = 3600
    zowpy_db_pool_timeout:int = 30
    zowpy_db_pool_pre_ping:bool = True


    # Logging
    zowpy_log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Instância global
settings = Settings()












