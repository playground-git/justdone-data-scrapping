import logging


def setup_logging(
    log_level=logging.INFO,
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
):
    """Set up logging configuration"""
    logging.basicConfig(level=log_level, format=log_format)
    logging.info("Logging configured")
