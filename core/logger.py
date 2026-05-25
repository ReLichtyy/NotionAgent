import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger that logs to file (INFO) and console (WARNING+)."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File handler for all INFO/DEBUG logs
        file_handler = logging.FileHandler("app_debug.log", encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '[%(levelname)s] %(asctime)s - %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Stream handler is removed to keep UI clean. 
        # All logs (INFO, WARNING, ERROR) will go strictly to app_debug.log.
        
    return logger
