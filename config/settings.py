
import os
from dataclasses import dataclass
from typing import List

@dataclass
class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./construction.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT", "120"))

    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")
    TEMPLATE_DIR: str = os.getenv("TEMPLATE_DIR", "templates")
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "backups")

    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = None

    DEFAULT_WORKWEEK: List[int] = None
    DEFAULT_SHIFT_HOURS: int = 8

    APP_NAME: str = "Construction Project Manager"
    APP_VERSION: str = "2.0.0"

    def __post_init__(self):
        if self.ALLOWED_EXTENSIONS is None:
            self.ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]
        if self.DEFAULT_WORKWEEK is None:
            self.DEFAULT_WORKWEEK = [0, 1, 2, 3, 4]

        for directory in [self.LOG_DIR, self.OUTPUT_DIR, self.TEMPLATE_DIR, self.BACKUP_DIR]:
            os.makedirs(directory, exist_ok=True)

settings = Settings()