import logging
import sys

GLOBAL_LOG_LEVEL = logging.CRITICAL


def get_logger(name: str) -> logging.Logger:
    """
    Creates a well-configured stdlib logger that outputs to stderr.
    """

    logger = logging.getLogger(name)
    logger.setLevel(GLOBAL_LOG_LEVEL)
    # Log to stderr, since stdout is used for actual IO
    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    return logger
