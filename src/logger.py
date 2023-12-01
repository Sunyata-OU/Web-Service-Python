import logging
import logging.handlers
import os
from src.config import Settings


def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(Settings.LOG_LEVEL)
    if not os.path.exists(Settings.LOG_PATH):
        try:
            os.makedirs(Settings.LOG_PATH)
        except OSError:
            Settings.LOG_PATH = "./logs/"
            os.makedirs(Settings.LOG_PATH)
    log_file = os.path.join(Settings.LOG_PATH, "webservice-logs.txt")

    rotating_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1024, backupCount=5)
    rotating_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    rotating_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(rotating_handler)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logger()
