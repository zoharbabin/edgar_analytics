"""
tests/test_logging_utils.py

Unit tests for the logging configuration functionality.
Verifies that:
1. Handlers are not duplicated on multiple configure_logging calls
2. Third-party logger levels are set correctly
3. Log level and suppress_logs parameters work as expected
4. Log file rotation is configured
"""

import logging
import logging.handlers
import os
from edgar_analytics.logging_utils import configure_logging, _get_log_directory


def test_no_duplicate_handlers():
    """Test that handlers are not duplicated when configure_logging is called multiple times."""
    logger = logging.getLogger("edgar_analytics")

    configure_logging("DEBUG")
    initial_handler_count = len(logger.handlers)
    assert initial_handler_count == 2, "Should have exactly 2 handlers (JSON and console)"

    configure_logging("INFO")
    assert len(logger.handlers) == initial_handler_count, "Handler count should not change on reconfiguration"

    configure_logging("WARNING", suppress_logs=True)
    assert len(logger.handlers) == initial_handler_count, "Handler count should not change with suppress_logs"


def test_third_party_logger_levels():
    """Test that third-party logger levels are set correctly based on chosen level."""
    third_party_loggers = ["edgar", "edgartools", "httpx"]

    configure_logging("INFO")
    for lib_name in third_party_loggers:
        logger = logging.getLogger(lib_name)
        assert logger.level == logging.WARNING, f"Third-party logger {lib_name} should be WARNING when not in DEBUG"

    configure_logging("DEBUG")
    for lib_name in third_party_loggers:
        logger = logging.getLogger(lib_name)
        assert logger.level == logging.DEBUG, f"Third-party logger {lib_name} should be DEBUG in DEBUG mode"


def test_log_level_setting():
    """Test that the main logger's level is set correctly."""
    logger = logging.getLogger("edgar_analytics")

    level_tests = [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
        ("invalid_level", logging.INFO),
    ]

    for level_str, expected_level in level_tests:
        configure_logging(level_str)
        assert logger.level == expected_level, f"Logger level should be {expected_level} when set to {level_str}"


def test_suppress_logs_console_handler():
    """Test that suppress_logs=True sets console handler to at least WARNING level."""
    logger = logging.getLogger("edgar_analytics")

    configure_logging("INFO", suppress_logs=True)
    console_handler = next(h for h in logger.handlers if "RichHandler" in h.__class__.__name__)
    assert console_handler.level >= logging.WARNING, "Suppressed logs should set console handler to WARNING or higher"

    configure_logging("DEBUG", suppress_logs=True)
    console_handler = next(h for h in logger.handlers if "RichHandler" in h.__class__.__name__)
    assert console_handler.level >= logging.WARNING, "Suppressed logs should maintain WARNING or higher with DEBUG"


def test_reconfigure_updates_existing_handlers():
    """Verify that calling configure_logging again updates handler levels rather than adding new ones."""
    logger = logging.getLogger("edgar_analytics")
    configure_logging("INFO")
    count_before = len(logger.handlers)

    configure_logging("DEBUG")
    assert len(logger.handlers) == count_before, "Handler count should not change"
    assert logger.level == logging.DEBUG, "Logger level should be updated to DEBUG"


def test_json_log_file_creation():
    """Test that the JSON log file is created in the platform log directory."""
    expected_path = os.path.join(_get_log_directory(), "edgar_analytics_debug.jsonl")

    configure_logging("DEBUG")

    logger = logging.getLogger("edgar_analytics")
    file_handler = next(h for h in logger.handlers if isinstance(h, logging.FileHandler))

    assert os.path.exists(expected_path), "JSON log file should be created"
    assert file_handler.baseFilename == expected_path, "FileHandler should use correct path"
    assert file_handler.level == logging.DEBUG, "JSON handler should always be at DEBUG level"
    assert isinstance(file_handler, logging.handlers.RotatingFileHandler), "Should use RotatingFileHandler"
