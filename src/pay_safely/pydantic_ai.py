"""Pydantic AI: a capability that checks a seller before an agent pays.

    from pydantic_ai import Agent
    from pay_safely import PaySafely
    from pay_safely.pydantic_ai import seller_check_capability

    agent = Agent("openai:gpt-4o", capabilities=[seller_check_capability(PaySafely(agent_id="buyer"))])

Needs: pip install "screwtape-pay-safely[pydantic-ai]"
"""
from __future__ import annotations

from typing import Optional

from pydantic_ai.capabilities import Capability

from ._util import run_check_text
from .core import PaySafely


def seller_check_capability(guard: Optional[PaySafely] = None) -> Capability:
    """A Pydantic AI capability with a tool: 'is this seller safe to pay?'"""
    guard = guard or PaySafely()
    capability = Capability(
        id="paysafely-seller-check",
        description=(
            "Check whether a seller is safe to pay before an agent pays, and return a signed receipt."
        ),
        instructions=(
            "Call check_seller_before_paying BEFORE paying any seller or paid API. "
            "Only pay when the answer starts with 'Safe to pay'."
        ),
    )

    @capability.tool_plain
    def check_seller_before_paying(seller_url: str, amount_usd: Optional[float] = None) -> str:
        """Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed
        receipt id. Only pay when the answer starts with 'Safe to pay'.

        Args:
            seller_url: Public https URL of the seller or paid endpoint you are about to pay.
            amount_usd: Amount in US dollars you intend to pay.
        """
        return run_check_text(guard, seller_url, amount_usd)[1]

    return capability
