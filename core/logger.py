import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger with standard formatting."""
    logger = logging.getLogger(name)
    
    # Only configure if it doesn't already have handlers
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(levelname)s] %(asctime)s - %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
