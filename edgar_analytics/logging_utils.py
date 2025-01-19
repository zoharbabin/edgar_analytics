# edgar_analytics/logging_utils.py

import logging
import sys


def get_logger(name=__name__, level=logging.DEBUG) -> logging.Logger:
    """
    Creates and returns a logger with a given name and level,
    configured to stream to stdout.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] "
            "[%(filename)s:%(lineno)d - %(funcName)s()] %(message)s"
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
