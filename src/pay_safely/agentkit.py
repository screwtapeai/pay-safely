"""AgentKit: an action provider with a 'check seller before paying' action.

    from coinbase_agentkit import AgentKit, AgentKitConfig
    from pay_safely import PaySafely
    from pay_safely.agentkit import pay_safely_action_provider

    agentkit = AgentKit(AgentKitConfig(..., action_providers=[pay_safely_action_provider(PaySafely(agent_id="buyer"))]))

Needs: pip install "screwtape-pay-safely[agentkit]"
"""
from __future__ import annotations

from typing import Any, Optional

from coinbase_agentkit import ActionProvider, create_action
from pydantic import BaseModel, Field

from ._util import run_check_text
from .core import PaySafely


class CheckSellerSchema(BaseModel):
    seller_url: str = Field(description="Public https URL of the seller or paid endpoint you are about to pay.")
    amount_usd: Optional[float] = Field(default=None, description="Amount in US dollars you intend to pay.")


class PaySafelyActionProvider(ActionProvider[Any]):
    def __init__(self, guard: Optional[PaySafely] = None):
        super().__init__("pay_safely", [])
        self.guard = guard or PaySafely()

    @create_action(
        name="check_seller_before_paying",
        description=(
            "Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed "
            "receipt id. Only pay when the answer starts with 'Safe to pay'."
        ),
        schema=CheckSellerSchema,
    )
    def check_seller_before_paying(self, args: dict[str, Any]) -> str:
        return run_check_text(self.guard, args["seller_url"], args.get("amount_usd"))[1]

    def supports_network(self, network: Any) -> bool:
        return True


def pay_safely_action_provider(guard: Optional[PaySafely] = None) -> PaySafelyActionProvider:
    return PaySafelyActionProvider(guard)
