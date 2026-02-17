# src/crawler/errors.py

class CrawlerError(Exception):
    """Base crawler exception."""


class TransientError(CrawlerError):
    """Temporary error (timeouts, 503, 429)."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class PermanentError(CrawlerError):
    """Non-recoverable error (404, 403, 401)."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class NetworkError(CrawlerError):
    """Network-level errors (DNS, connection refused)."""


class ParseError(CrawlerError):
    """HTML parsing error."""
