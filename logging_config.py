import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging():
    # Root logger
    logging.basicConfig(level=logging.INFO)
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Clear default handlers

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # App log (your prints go here)
    app_handler = RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=10_000_000,
        backupCount=5
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)

    # Error log
    error_handler = RotatingFileHandler(
        f"{LOG_DIR}/error.log",
        maxBytes=10_000_000,
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)

    # Silence Werkzeug access logs
    noisy_libs = {
    "urllib3": logging.WARNING,
    "requests": logging.WARNING,
    "azure": logging.WARNING,
    "azure.identity": logging.WARNING,
    "azure.core": logging.WARNING,
    "msal": logging.WARNING,
    "presidio_analyzer": logging.WARNING,
    "werkzeug": logging.WARNING,
    "langchain": logging.INFO,   # keep high-level visibility
    }

    for lib, lvl in noisy_libs.items():
        logging.getLogger(lib).setLevel(lvl)
