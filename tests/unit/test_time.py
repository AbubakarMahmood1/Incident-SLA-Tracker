from datetime import UTC, datetime

import pytest

from app.utils import FixedClock, SystemClock


def test_system_clock_is_timezone_aware() -> None:
    value = SystemClock().now()
    assert value.tzinfo is not None
    assert value.utcoffset() is not None


def test_fixed_clock_returns_exact_value() -> None:
    value = datetime(2026, 7, 27, tzinfo=UTC)
    assert FixedClock(value).now() == value


def test_fixed_clock_rejects_naive_value() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FixedClock(datetime(2026, 7, 27))
