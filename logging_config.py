import logging
from logging.handlers import RotatingFileHandler
import os

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOG_BASE_DIR = "/mnt/adlscontainer/CreditIQ/logs"
SERVICE_NAME = "python_srv"

APP_ENV = os.getenv("APP_ENV", "dev").lower()

LOG_LEVEL = logging.DEBUG if APP_ENV == "dev" else logging.INFO

LOG_DIR = f"{LOG_BASE_DIR}/{APP_ENV}/{SERVICE_NAME}"
os.makedirs(LOG_DIR, exist_ok=True)

MAX_BYTES = 10_000_000
BACKUP_COUNT = 5


def setup_logging():
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # App log (your prints go here)
    app_handler = RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    app_handler.setLevel(LOG_LEVEL)
    app_handler.setFormatter(formatter)
    
    # Error log
    error_handler = RotatingFileHandler(
        f"{LOG_DIR}/error.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )

    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    app_logger = logging.getLogger("ragBackend")
    app_logger.setLevel(LOG_LEVEL)
    app_logger.handlers.clear()
    app_logger.addHandler(app_handler)
    app_logger.addHandler(error_handler)
    app_logger.propagate = False

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)


    # Silence noisy libraries
    noisy_libs = [
        "urllib3",
        "requests",
        "azure",
        "azure.identity",
        "azure.core",
        "azure.core.pipeline",
        "azure.core.pipeline.policies.http_logging_policy",
        "msal",
        "presidio",
        "presidio_analyzer",
        "werkzeug",
    ]

    for lib in noisy_libs:
        lib_logger = logging.getLogger(lib)
        lib_logger.setLevel(logging.WARNING)
        lib_logger.propagate = False

    return app_logger
