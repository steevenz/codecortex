"""
/**
 * @project   CodeCortex
 * @package   Core/Logging
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-Logging-v1.0
 * @stack     Python
 * * Structured logging configuration for production-ready observability.
 */
"""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
import json


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON for structured logging.
    """
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "context": record.name,
            "message": record.getMessage(),
        }
        
        # Extract standard top-level fields if passed via extra
        standard_fields = [
            "service", "environment", "version", 
            "user_id", "tenant_id", "organization_id", "workspace_id", 
            "request_id", "trace_id", "error_code", "duration_ms",
            "inbound", "outbound"
        ]
        
        for field in standard_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
                
        # Add extra context if passed via extra={"context": {...}}
        if hasattr(record, 'context') and isinstance(record.context, dict):
            for k, v in record.context.items():
                if k not in log_entry:
                    log_entry[k] = v
        
        # Add exception info if present
        if record.exc_info:
            exc_type = record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else "Exception"
            exc_val = record.exc_info[1]
            if "error_message" not in log_entry:
                log_entry["error_message"] = str(exc_val) if exc_val is not None else ""
            
            if os.getenv("ENV", "development").strip().lower() != "production" or os.getenv("CODECORTEX_LOG_STACKTRACE", "0").strip().lower() in {"1", "true", "yes", "on"}:
                log_entry["stack_trace"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class LoggerConfig:
    """
    Centralized logging configuration for CodeCortex.
    """
    _configured = False
    
    @classmethod
    def setup(cls, log_level: str = "INFO"):
        """
        Configure structured logging for the application.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARN, ERROR)
        """
        if cls._configured:
            return
        
        # Aegis Standard: project_root / outputs / logs / {environment} / {YYYY-MM-DD}
        project_root = Path(__file__).resolve().parents[2]
        env = os.getenv("ENV", "development").strip().lower()
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        standard_log_path = project_root / "outputs" / "logs" / env / date_str
        standard_log_path.mkdir(parents=True, exist_ok=True)
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        console_format = os.getenv("CODECORTEX_LOG_CONSOLE_FORMAT", "json").strip().lower()
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        if console_format == "pretty":
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        else:
            console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)
        
        # File handler with structured JSON (application log)
        app_log_file = standard_log_path / "application.log"
        file_handler = RotatingFileHandler(
            app_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_file = standard_log_path / "error.log"
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
        
        cls._configured = True
        
        # Log initialization
        logging.getLogger("CodeCortex").info("Logging system initialized", extra={
            "context": {
                "log_level": log_level, 
                "log_dir": str(standard_log_path), 
                "console_format": console_format,
                "project_root": str(project_root)
            }
        })
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.
        
        Args:
            name: Logger name (typically __name__)
        
        Returns:
            Configured logger instance
        """
        if not cls._configured:
            cls.setup()
        
        return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return LoggerConfig.get_logger(name)
