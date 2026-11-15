"""OpenAI Agents SDK: a check tool, and a guardrail that stops a payment tool unless the seller is allowed.

    from agents import Agent
    from pay_safely import PaySafely
    from pay_safely.openai_agents import seller_check_tool, payment_guardrail

    guard = PaySafely(agent_id="buyer")
    pay = function_tool(pay_seller, tool_input_guardrails=[payment_guardrail(guard, seller_url_arg="url", amount_arg="usd")])
    agent = Agent(name="Buyer", tools=[seller_check_tool(guard), pay])

Needs: pip install "screwtape-pay-safely[openai-agents]"
"""
from __future__ import annotations

import json
from typing import Optional

from agents import ToolGuardrailFunctionOutput, ToolInputGuardrail, ToolInputGuardrailData, function_tool

from ._util import run_check_text
from .core import PaySafely


def seller_check_tool(guard: PaySafely):
    """A function tool the agent can call: 'is this seller safe to pay?'"""

    @function_tool(name_override="check_seller_before_paying")
    def check_seller_before_paying(seller_url: str, amount_usd: Optional[float] = None) -> str:
        """Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed
        receipt id. Only pay when the answer starts with 'Safe to pay'.

        Args:
            seller_url: Public https URL of the seller or paid endpoint you are about to pay.
            amount_usd: Amount in US dollars you intend to pay.
        """
        return run_check_text(guard, seller_url, amount_usd)[1]

    return check_seller_before_paying


def payment_guardrail(guard: PaySafely, seller_url_arg: str, amount_arg: Optional[str] = None) -> ToolInputGuardrail:
    """A tool input guardrail. Put it on your payment tool; the tool runs only when the seller check allows it."""

    def run(data: ToolInputGuardrailData) -> ToolGuardrailFunctionOutput:
        try:
            args = json.loads(data.context.tool_arguments or "{}")
        except ValueError:
            args = {}
        amount = args.get(amount_arg) if amount_arg else None
        ok, message = run_check_text(guard, args.get(seller_url_arg), float(amount) if amount is not None else None)
        if ok:
            return ToolGuardrailFunctionOutput.allow(output_info=message)
        return ToolGuardrailFunctionOutput.reject_content(f"Payment not made. {message}", output_info=message)

    return ToolInputGuardrail(guardrail_function=run, name="pay_safely_seller_check")
