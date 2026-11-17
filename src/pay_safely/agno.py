"""Agno: a toolkit that checks a seller before an agent pays.

    from agno.agent import Agent
    from pay_safely import PaySafely
    from pay_safely.agno import SellerCheckTools

    agent = Agent(tools=[SellerCheckTools(guard=PaySafely(agent_id="buyer"))])

Needs: pip install "screwtape-pay-safely[agno]"
"""
from __future__ import annotations

from typing import Optional

from agno.tools.toolkit import Toolkit

from ._util import run_check_text
from .core import PaySafely


class SellerCheckTools(Toolkit):
    """Agno toolkit: check whether a seller is safe to pay, and return a signed receipt."""

    def __init__(self, guard: Optional[PaySafely] = None, **kwargs):
        self.guard = guard or PaySafely()
        super().__init__(
            name="paysafely_seller_check",
            tools=[self.check_seller_before_paying],
            instructions=(
                "Call check_seller_before_paying BEFORE paying any seller or paid API. "
                "Only pay when the answer starts with 'Safe to pay'."
            ),
            add_instructions=True,
            **kwargs,
        )

    def check_seller_before_paying(self, seller_url: str, amount_usd: Optional[float] = None) -> str:
        """Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed
        receipt id. Only pay when the answer starts with 'Safe to pay'.

        Args:
            seller_url: Public https URL of the seller or paid endpoint you are about to pay.
            amount_usd: Amount in US dollars you intend to pay.
        """
        return run_check_text(self.guard, seller_url, amount_usd)[1]
