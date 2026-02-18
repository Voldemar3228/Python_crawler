import logging
import colorlog
from logging.handlers import RotatingFileHandler
from tqdm import tqdm
import sys

class TqdmLoggingHandler(logging.Handler):
    """Логгер, который корректно пишет через tqdm.write(), не ломая прогресс-бар."""
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


import logging
import colorlog
import sys


def setup_crawler_logger(level=logging.DEBUG, log_file=None) -> logging.Logger:
    """
    Настраивает цветной логгер для AsyncCrawler.
    Поддерживает UTF-8 (эмодзи) даже в Windows.
    """

    logger = colorlog.getLogger("crawler")
    logger.setLevel(level)
    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    # 🔹 Включаем UTF-8 для Windows
    if sys.platform.startswith("win"):
        sys.stdout.reconfigure(encoding="utf-8")

    console_handler = colorlog.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s] %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }
        )
    )

    logger.addHandler(console_handler)

    return logger

