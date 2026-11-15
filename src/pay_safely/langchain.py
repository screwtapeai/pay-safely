"""LangChain and LangGraph: a tool that checks a seller, and a wrapper that checks before a payment tool runs.

    from pay_safely import PaySafely
    from pay_safely.langchain import seller_check_tool, guard_tool

    guard = PaySafely(agent_id="my-agent")
    tools = [seller_check_tool(guard), guard_tool(my_payment_tool, guard, seller_url_arg="url", amount_arg="usd")]

Works with `create_react_agent` (LangGraph) and with any LangChain agent that takes tools.
Needs: pip install "screwtape-pay-safely[langchain]"
"""
from __future__ import annotations

from typing import Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from ._util import run_check_text
from .core import PaySafely


class _SellerCheckInput(BaseModel):
    seller_url: str = Field(description="Public https URL of the seller or paid endpoint you are about to pay.")
    amount_usd: Optional[float] = Field(default=None, description="Amount in US dollars you intend to pay.")


def seller_check_tool(guard: PaySafely) -> StructuredTool:
    """A tool the agent can call: 'is this seller safe to pay?'"""

    def check_seller_before_paying(seller_url: str, amount_usd: Optional[float] = None) -> str:
        return run_check_text(guard, seller_url, amount_usd)[1]

    return StructuredTool.from_function(
        func=check_seller_before_paying,
        name="check_seller_before_paying",
        description=(
            "Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed "
            "receipt id. Only pay when the answer starts with 'Safe to pay'."
        ),
        args_schema=_SellerCheckInput,
    )


def guard_tool(tool: BaseTool, guard: PaySafely, seller_url_arg: str, amount_arg: Optional[str] = None) -> StructuredTool:
    """Wrap a payment tool so the seller check runs first. The payment tool only runs on an allow verdict.

    seller_url_arg: name of the tool argument that holds the seller URL.
    amount_arg: name of the tool argument that holds the amount in dollars (optional).
    """

    def guarded(**kwargs):
        url = kwargs.get(seller_url_arg)
        amount = kwargs.get(amount_arg) if amount_arg else None
        ok, message = run_check_text(guard, url, float(amount) if amount is not None else None)
        if not ok:
            return f"Payment not made. {message}"
        return tool.invoke(kwargs)

    return StructuredTool.from_function(
        func=guarded,
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        infer_schema=False,
    )
