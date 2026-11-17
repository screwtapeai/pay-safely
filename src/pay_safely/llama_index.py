"""LlamaIndex: a tool that checks a seller before an agent pays.

    from pay_safely import PaySafely
    from pay_safely.llama_index import seller_check_tool

    tools = [seller_check_tool(PaySafely(agent_id="buyer"))]

Needs: pip install "screwtape-pay-safely[llama-index]"
"""
from __future__ import annotations

from typing import Optional

from llama_index.core.tools import FunctionTool

from ._util import run_check_text
from .core import PaySafely


def seller_check_tool(guard: Optional[PaySafely] = None) -> FunctionTool:
    """A LlamaIndex FunctionTool the agent can call: 'is this seller safe to pay?'"""
    guard = guard or PaySafely()

    def check_seller_before_paying(seller_url: str, amount_usd: Optional[float] = None) -> str:
        """Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed
        receipt id. Only pay when the answer starts with 'Safe to pay'.
        """
        return run_check_text(guard, seller_url, amount_usd)[1]

    return FunctionTool.from_defaults(
        fn=check_seller_before_paying,
        name="check_seller_before_paying",
        description=(
            "Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed "
            "receipt id. Only pay when the answer starts with 'Safe to pay'."
        ),
    )
