"""
Logging configuration for construction management app
"""

import logging
import sys
import os
from pathlib import Path

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Set up logging configuration for the application
    """
    if log_file is None:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "construction_app.log"
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('streamlit').setLevel(logging.WARNING)

def get_logger(name):
    """Get a logger instance with the given name"""
    return logging.getLogger(name)