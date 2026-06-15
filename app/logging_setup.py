"""Observability and logging setup for CarbonCompass.

This module initializes the structured logging environment, attempting to bind
to Google Cloud Logging if available, with a standard library fallback.
"""

import logging


def setup_logging() -> logging.Logger:
    """Initialize and return the application logger.

    Attempts to configure Google Cloud Logging. If that fails or is not available,
    falls back to stdlib configuration.

    Returns:
        logging.Logger: The configured application logger instance.
    """
    logger = logging.getLogger("carboncompass")
    logger.setLevel(logging.INFO)

    # Prevent appending multiple handlers if called repeatedly
    if not logger.handlers:
        try:
            import google.cloud.logging

            cloud_client = google.cloud.logging.Client()
            cloud_client.setup_logging()
            logger.info("Google Cloud Logging initialised.")
        except ImportError:
            logging.basicConfig(level=logging.INFO)
            logger.info("Falling back to standard logging due to import error.")
        except Exception:
            logging.basicConfig(level=logging.INFO)
            logger.info("Falling back to standard logging due to initialization error.")

    return logger
