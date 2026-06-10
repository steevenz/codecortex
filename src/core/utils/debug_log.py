"""
Pre-configured logger instances for debug/diagnostic output.

:project: CodeCortex
:package: Core.Utils.Debug_log
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Core-v1.0
"""

from src.core.logging import get_logger

info_logger = get_logger('info')
error_logger = get_logger('error')
warning_logger = get_logger('warning')


def log_info(msg: str):
    info_logger.info(msg)


def log_error(msg: str):
    error_logger.error(msg)


def log_warning(msg: str):
    warning_logger.warning(msg)