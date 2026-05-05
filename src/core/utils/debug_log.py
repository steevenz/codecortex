"""
/**
 * @project   CodeCortex
 * @package   Core/Utils
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Debug / info / error logging utilities used by Tree-sitter and indexing layers.
 */
"""

from __future__ import annotations

from ..logging_config import get_logger

logger = get_logger("CodeCortex.Utils.Debug")


def debug_log(msg: str) -> None:
    logger.debug(msg)


def info_logger(msg: str) -> None:
    logger.info(msg)


def warning_logger(msg: str) -> None:
    logger.warning(msg)


def error_logger(msg: str) -> None:
    logger.error(msg)


def debug_logger(msg: str) -> None:
    logger.debug(msg)
