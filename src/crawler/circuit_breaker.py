# src/crawler/circuit_breaker.py
import time
from collections import defaultdict, deque

class CircuitBreaker:
    """
    Простой circuit breaker для доменов.
    - Отслеживает ошибки по домену
    - Блокирует домен, если частота ошибок превышает threshold
    - Автоматически восстанавливается через reset_timeout
    """

    def __init__(self, max_errors: int = 5, window: float = 60.0, reset_timeout: float = 30.0):
        """
        :param max_errors: максимальное количество ошибок в окне времени
        :param window: окно времени в секундах для подсчёта ошибок
        :param reset_timeout: время блокировки домена в секундах
        """
        self.max_errors = max_errors
        self.window = window
        self.reset_timeout = reset_timeout

        # структура: {domain: deque[timestamp ошибок]}
        self.errors = defaultdict(deque)

        # блокировки: {domain: unblock_time}
        self.blocked_domains = {}

    def record_error(self, domain: str):
        """Записываем ошибку для домена"""
        now = time.time()
        q = self.errors[domain]

        # удаляем старые ошибки вне окна
        while q and now - q[0] > self.window:
            q.popleft()

        q.append(now)

        # если превышен порог → блокируем домен
        if len(q) >= self.max_errors:
            self.blocked_domains[domain] = now + self.reset_timeout

    def is_blocked(self, domain: str) -> bool:
        """Проверяем, заблокирован ли домен"""
        unblock_time = self.blocked_domains.get(domain)
        if unblock_time is None:
            return False

        if time.time() >= unblock_time:
            # сбрасываем блокировку
            del self.blocked_domains[domain]
            self.errors[domain].clear()
            return False
        return True

    def get_remaining_block(self, domain: str) -> float:
        """Возвращает оставшееся время блокировки, если есть"""
        unblock_time = self.blocked_domains.get(domain)
        if unblock_time:
            return max(0, unblock_time - time.time())
        return 0.0
