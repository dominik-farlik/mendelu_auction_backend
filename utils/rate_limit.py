import time
from collections import deque

from fastapi import HTTPException, Request
from starlette import status

MAX_TRACKED_KEYS = 10_000


class RateLimiter:
    """
    Jednoduchý limiter s posuvným oknem držený v paměti procesu.
    Při více workerech má každý worker vlastní počítadla.
    """

    def __init__(self):
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())

        while hits and hits[0] <= now - window_seconds:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = int(hits[0] + window_seconds - now) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Příliš mnoho pokusů, zkuste to prosím později.",
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)

        if len(self._hits) > MAX_TRACKED_KEYS:
            self._purge(now, window_seconds)

    def _purge(self, now: float, window_seconds: int) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - window_seconds]:
            del self._hits[key]


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int):
    """FastAPI dependency omezující počet požadavků z jedné IP adresy."""

    def dependency(request: Request) -> None:
        limiter.hit(f"{scope}:ip:{client_ip(request)}", limit, window_seconds)

    return dependency


def rate_limit_key(scope: str, key: str, limit: int, window_seconds: int) -> None:
    """Omezení podle libovolného klíče (např. e-mailu), volané přímo z endpointu."""
    limiter.hit(f"{scope}:key:{key.strip().lower()}", limit, window_seconds)
