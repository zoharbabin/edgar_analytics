"""
edgar_analytics/logging_utils.py

Provides logging configuration with:
 - Rich colorized console logs at a chosen level.
 - JSON logs at DEBUG level stored in 'edgar_analytics_debug.jsonl'.
 - Optionally suppress normal console logs if the user sets --suppress-logs.
"""

import logging
import os
import json
from typing import Any, Dict, Optional
from rich.logging import RichHandler


class JSONFormatter(logging.Formatter):
    """
    Custom JSON Formatter: each log record -> single-line JSON object.
    Useful for ingestion by log management systems (Splunk, Elastic, etc.).
    """

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


def configure_logging(log_level: str, suppress_logs: bool = False) -> None:
    """
    Configure logging for edgar_analytics.

    Args:
        log_level: e.g., 'DEBUG', 'INFO', etc.
        suppress_logs: If True, minimize console logs and show only final output.
    """
    valid_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    chosen_level = valid_levels.get(log_level.upper(), logging.INFO)

    # Get the edgar_analytics logger and set its level
    edgar_logger = logging.getLogger("edgar_analytics")

    # JSON logs file handler at DEBUG
    debug_file_path = os.path.join(os.getcwd(), "edgar_analytics_debug.jsonl")
    json_formatter = JSONFormatter()
    json_file_handler = logging.FileHandler(debug_file_path, mode='a', encoding='utf-8')
    json_file_handler.setLevel(logging.DEBUG)
    json_file_handler.setFormatter(json_formatter)


    # Rich console handler
    if suppress_logs:
        # If user wants minimal logs, set console handler to WARNING or higher
        console_log_level = max(chosen_level, logging.WARNING)
    else:
        console_log_level = chosen_level

    console_handler = RichHandler(
        level=console_log_level,
        markup=True,
        show_time=False,
        show_level=True,
        show_path=False
    )

    # Set logger level and prevent duplicate handler registration
    edgar_logger.setLevel(chosen_level)
    
    # Only add handlers if none exist
    if not edgar_logger.handlers:
        edgar_logger.addHandler(json_file_handler)
        edgar_logger.addHandler(console_handler)
    # Note: We don't update existing handlers as per ADR decision

    # Third-party loggers, adjusted for noise if not DEBUG
    third_party_loggers = ["edgar", "edgartools", "httpx"]
    if chosen_level != logging.DEBUG:
        for lib_name in third_party_loggers:
            logging.getLogger(lib_name).setLevel(logging.WARNING)
    else:
        for lib_name in third_party_loggers:
            logging.getLogger(lib_name).setLevel(logging.DEBUG)

    if chosen_level == logging.DEBUG:
        logging.debug(
            "[bold magenta]Console log level: DEBUG.[/bold magenta] "
            f"Detailed JSON logs in '{debug_file_path}'."
        )
    else:
        logging.info(
            f"[bold green]Console log level: {log_level.upper()}[/bold green]. "
            f"Detailed DEBUG logs in JSON => '{debug_file_path}'."
        )


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Return a standard Python logger for the given module-level name.
    """
    return logging.getLogger(name)
