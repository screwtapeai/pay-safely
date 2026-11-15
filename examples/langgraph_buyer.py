"""A LangGraph agent that checks a seller before it pays. Replace pay_seller with your real payment call."""
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from pay_safely import PaySafely
from pay_safely.langchain import guard_tool, seller_check_tool

guard = PaySafely(agent_id="demo-buyer")


@tool
def pay_seller(url: str, usd: float) -> str:
    """Pay a seller the given amount in US dollars."""
    return f"Paid ${usd} to {url}"


agent = create_react_agent(
    "openai:gpt-4o-mini",
    [seller_check_tool(guard), guard_tool(pay_seller, guard, seller_url_arg="url", amount_arg="usd")],
)
