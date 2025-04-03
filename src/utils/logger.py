import logging
from src.config.settings import LOG_LEVEL

def setup_logger(name, log_file='app.log'):
    """
    Set up logger with consistent configuration to log to both console and file.
    
    :param name: Name of the logger.
    :param log_file: Path to the log file.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times if the logger already exists
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    logger.setLevel(LOG_LEVEL)
    return logger
