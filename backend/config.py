"""
Configuration management for JenteraPintar P170 Tuaran.
Menyokong environment variables untuk production deployment.
Semua konfigurasi sensitif diambil dari environment variables, BUKAN hardcoded.
"""
import os
from typing import Optional

# Auto-load .env file jika wujud
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

class Settings:
    # === JWT & AUTH ===
    SECRET_KEY: str = os.environ.get(
        "JENTERA_SECRET_KEY",
        # Fallback untuk development sahaja. Dalam production, WAJIB set env var.
        "kunci-rahasia-dun-matunggong-2026"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.environ.get("JENTERA_TOKEN_EXPIRE_HOURS", "24"))

    # === DATABASE (SQLite - default) ===
    DB_PATH: str = os.environ.get(
        "JENTERA_DB_PATH",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pengundi.db')
    )

    # === DATABASE (PostgreSQL via DATABASE_URL) ===
    # Jika environment variable DATABASE_URL diset, sistem akan guna PostgreSQL.
    # Format: postgresql://user:password@host:port/dbname
    DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")

    # === CORS ===
    # Dalam production, set JENTERA_ALLOWED_ORIGINS ke domain tertentu
    ALLOWED_ORIGINS: list = os.environ.get(
        "JENTERA_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8000"
    ).split(",")

    # === DEPLOYMENT MODE ===
    DEBUG: bool = os.environ.get("JENTERA_DEBUG", "true").lower() == "true"
    PRODUCTION: bool = os.environ.get("JENTERA_PRODUCTION", "false").lower() == "true"

    # === STATIC FILES (Production) ===
    STATIC_DIR: str = os.environ.get(
        "JENTERA_STATIC_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
    )

    # === LOGGING ===
    LOG_FILE: Optional[str] = os.environ.get("JENTERA_LOG_FILE")

    @property
    def is_production(self) -> bool:
        return self.PRODUCTION

    @property
    def cors_origins(self) -> list:
        if self.PRODUCTION:
            # Dalam production, hanya domain yang dibenarkan
            return self.ALLOWED_ORIGINS
        # Dalam development, benarkan semua
        return ["*"]


settings = Settings()