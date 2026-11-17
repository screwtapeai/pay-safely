"""Haystack: a component that checks a seller before an agent pays.

    from pay_safely import PaySafely
    from pay_safely.haystack import SellerCheck

    check = SellerCheck(guard=PaySafely(agent_id="buyer"))
    result = check.run(seller_url="https://seller.example/pay", amount_usd=0.05)
    # result["result"] starts with "Safe to pay" when the seller is allowed.

Needs: pip install "screwtape-pay-safely[haystack]"
"""
from __future__ import annotations

from typing import Any, Optional

from haystack import component

from ._util import run_check_text
from .core import PaySafely


@component
class SellerCheck:
    """Haystack component: check whether a seller is safe to pay, and return a signed receipt."""

    def __init__(self, guard: Optional[PaySafely] = None):
        self.guard = guard or PaySafely()

    @component.output_types(result=str)
    def run(self, seller_url: str, amount_usd: Optional[float] = None) -> dict[str, Any]:
        """Call this BEFORE paying any seller or paid API.

        Returns a string starting with 'Safe to pay' only when the check allows the payment.
        """
        return {"result": run_check_text(self.guard, seller_url, amount_usd)[1]}
