"""
edgar_analytics/logging_utils.py

Provides logging configuration with:
 - Rich colorized console logs at a chosen level.
 - JSON logs at DEBUG level stored in 'edgar_analytics_debug.jsonl' (with rotation).
 - Optionally suppress normal console logs if the user sets --suppress-logs.
"""

import atexit
import logging
import logging.handlers
import os
import json
import sys
from typing import Any, Dict
from rich.logging import RichHandler

_THIRD_PARTY_LOGGERS = ("edgar", "edgartools", "httpx")
_LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_LOG_FILE_BACKUP_COUNT = 3


def _get_log_directory() -> str:
    """Return a platform-appropriate directory for log files."""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Logs")
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
    log_dir = os.path.join(base, "edgar_analytics")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


class JSONFormatter(logging.Formatter):
    """Custom JSON Formatter: each log record -> single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def configure_logging(
    log_level: str,
    suppress_logs: bool = False,
    enable_file_logging: bool = False,
) -> None:
    """Configure logging for edgar_analytics.

    Args:
        log_level: e.g., 'DEBUG', 'INFO', etc.
        suppress_logs: If True, minimize console logs and show only final output.
        enable_file_logging: If True, write debug JSON logs to disk.
            Defaults to False so library consumers don't get surprise log files.
            The CLI sets this to True automatically.
    """
    valid_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    chosen_level = valid_levels.get(log_level.upper(), logging.INFO)
    console_log_level = max(chosen_level, logging.WARNING) if suppress_logs else chosen_level

    edgar_logger = logging.getLogger("edgar_analytics")
    edgar_logger.setLevel(chosen_level)

    if not edgar_logger.handlers:
        if enable_file_logging:
            debug_file_path = os.path.join(_get_log_directory(), "edgar_analytics_debug.jsonl")
            json_file_handler = logging.handlers.RotatingFileHandler(
                debug_file_path, mode='a', encoding='utf-8',
                maxBytes=_LOG_FILE_MAX_BYTES, backupCount=_LOG_FILE_BACKUP_COUNT,
            )
            json_file_handler.setLevel(logging.DEBUG)
            json_file_handler.setFormatter(JSONFormatter())
            edgar_logger.addHandler(json_file_handler)

        console_handler = RichHandler(
            level=console_log_level,
            markup=True,
            show_time=False,
            show_level=True,
            show_path=False
        )

        edgar_logger.addHandler(console_handler)

        atexit.register(_shutdown_logging)
    else:
        for h in edgar_logger.handlers:
            if isinstance(h, logging.FileHandler):
                h.setLevel(logging.DEBUG)
            elif isinstance(h, RichHandler):
                h.setLevel(console_log_level)

    third_party_level = logging.DEBUG if chosen_level == logging.DEBUG else logging.WARNING
    for lib_name in _THIRD_PARTY_LOGGERS:
        logging.getLogger(lib_name).setLevel(third_party_level)


def _shutdown_logging() -> None:
    """Flush and close all handlers on the edgar_analytics logger."""
    edgar_logger = logging.getLogger("edgar_analytics")
    for handler in edgar_logger.handlers:
        handler.flush()
        handler.close()


def get_logger(name: str = __name__) -> logging.Logger:
    """Return a standard Python logger for the given module-level name."""
    return logging.getLogger(name)
