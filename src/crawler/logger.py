import logging
import colorlog

def setup_crawler_logger(level=logging.DEBUG) -> logging.Logger:
    """
    Configuring a color logger for AsyncCrawler.
    Shows only manual logs (not system aiohttp/Python ones).
    /
    Настраивает цветной логгер для AsyncCrawler.
    Будут выводиться только ручные логи (не системные aiohttp/Python).
    """
    logger = colorlog.getLogger("crawler")  # matches with logger в crawler.py
    logger.setLevel(level)
    logger.propagate = False  # turn off root logger output

    if logger.hasHandlers():
        logger.handlers.clear()

    handler = colorlog.StreamHandler()
    handler.setFormatter(
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
    logger.addHandler(handler)
    return logger
