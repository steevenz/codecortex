"""
@project   CodeCortex
@package   modules.idegraph.core.logging
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.core.logging
:standard: Aegis-IdeGraph-v1.0

Logging Service — Structured JSON logging for SideCortex.
"""

import os
import json
import logging
import logging.handlers
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """
    def __init__(self, service: str, environment: str, version: str):
        super().__init__()
        self.service = service
        self.environment = environment
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            "level": record.levelname.lower(),
            "context": record.name,
            "message": record.getMessage()[:120],
            "service": self.service,
            "environment": self.environment,
            "version": self.version,
            "user_id": getattr(record, 'user_id', None),
            "tenant_id": getattr(record, 'tenant_id', None),
            "organization_id": getattr(record, 'organization_id', None),
            "workspace_id": getattr(record, 'workspace_id', None),
            "request_id": getattr(record, 'request_id', None),
        }
        
        # Add extra fields if provided
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
            
        # Error handling
        if record.levelno >= logging.ERROR:
            log_data["error_code"] = getattr(record, 'error_code', 'INTERNAL_ERROR')
            log_data["error_message"] = str(record.msg)
            if record.exc_info and record.exc_info[0] is not None:
                log_data["exception_type"] = record.exc_info[0].__name__

        return json.dumps(log_data, ensure_ascii=False, separators=(",", ":"))

class LoggingService:
    """
    Service to manage structured JSON logging.
    """
    def __init__(self, app_name: str = "SideCortex"):
        self.app_name = app_name
        self.root_path = Path(os.getcwd())
        self.env = os.getenv("ENV", "development")
        self.version = self._load_version()
        self.log_dir = self.root_path / "outputs" / "logs" / self.env / datetime.now().strftime('%Y-%m-%d')
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _load_version(self) -> str:
        version_file = self.root_path / ".version"
        if version_file.exists():
            return version_file.read_text().strip()
        return "0.1.0"

    def _setup_handlers(self):
        formatter = JsonFormatter(self.app_name, self.env, self.version)

        max_bytes = int(os.getenv("LOG_MAX_BYTES", "10_000_000").replace("_", ""))
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

        # Application Log with rotation
        app_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "application.log",
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        app_handler.setFormatter(formatter)
        self.logger.addHandler(app_handler)

        # Error Log with rotation
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

        # Console Output (for development)
        if self.env == "development":
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def get_logger(self, context: Optional[str] = None):
        if context:
            return self.logger.getChild(context)
        return self.logger

# Global singleton for easy access
_logging_service = None
_singleton_lock = threading.Lock()

def get_logger(context: Optional[str] = None):
    global _logging_service
    with _singleton_lock:
        if _logging_service is None:
            _logging_service = LoggingService()
    return _logging_service.get_logger(context)
