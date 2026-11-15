"""CrewAI: a tool that checks a seller before the crew pays.

    from pay_safely import PaySafely
    from pay_safely.crewai import SellerCheckTool

    agent = Agent(role="Buyer", goal="...", backstory="...", tools=[SellerCheckTool(guard=PaySafely(agent_id="buyer"))])

Needs: pip install "screwtape-pay-safely[crewai]"
"""
from __future__ import annotations

from typing import Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from ._util import run_check_text
from .core import PaySafely


class SellerCheckInput(BaseModel):
    seller_url: str = Field(..., description="Public https URL of the seller or paid endpoint you are about to pay.")
    amount_usd: Optional[float] = Field(default=None, description="Amount in US dollars you intend to pay.")


class SellerCheckTool(BaseTool):
    name: str = "check_seller_before_paying"
    description: str = (
        "Call this BEFORE paying any seller or paid API. Returns ALLOW, REVIEW or BLOCK with reasons and a signed "
        "receipt id. Only pay when the answer starts with 'Safe to pay'."
    )
    args_schema: Type[BaseModel] = SellerCheckInput
    guard: Any = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, seller_url: str, amount_usd: Optional[float] = None) -> str:
        guard = self.guard or PaySafely()
        return run_check_text(guard, seller_url, amount_usd)[1]
