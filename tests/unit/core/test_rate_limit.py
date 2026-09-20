"""
Unit tests for rate limiting configuration.
"""
from slowapi import Limiter

from core.config import settings
from core.rate_limit import limiter


def test_limiter_is_configured():
    assert isinstance(limiter, Limiter)
    assert callable(limiter._key_func)
    assert limiter.enabled is settings.RATE_LIMIT_ENABLED
