from decimal import Decimal

import pytest

from raven.core.types import quantize_money


def test_quantize_money_uses_decimal_rounding() -> None:
    assert quantize_money(Decimal("10.005")) == Decimal("10.01")
    assert quantize_money(Decimal("10.004")) == Decimal("10.00")


def test_quantize_money_rejects_float() -> None:
    with pytest.raises(TypeError):
        quantize_money(10.005)  # type: ignore[arg-type]
