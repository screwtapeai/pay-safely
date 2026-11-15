import json

import pytest

from pay_safely import PaySafely


def guard_with(verdict):
    return PaySafely(transport=lambda url, body, headers, timeout: (200, {"verdict": verdict, "reasons": ["r"], "receipt_id": "rid"}))


def test_langchain_guard_tool_blocks_and_allows():
    pytest.importorskip("langchain_core")
    from langchain_core.tools import StructuredTool

    from pay_safely.langchain import guard_tool, seller_check_tool

    calls = []

    def pay(url: str, usd: float) -> str:
        calls.append(url)
        return "paid"

    base = StructuredTool.from_function(pay, name="pay", description="Pay a seller")
    blocked = guard_tool(base, guard_with("block"), "url", "usd")
    assert "Payment not made" in blocked.invoke({"url": "https://seller.example/p", "usd": 1})
    assert calls == []
    allowed = guard_tool(base, guard_with("allow"), "url", "usd")
    assert allowed.invoke({"url": "https://seller.example/p", "usd": 1}) == "paid"
    assert calls == ["https://seller.example/p"]
    assert seller_check_tool(guard_with("allow")).invoke({"seller_url": "https://seller.example/p"}).startswith("Safe to pay")


def test_openai_agents_tool_and_guardrail():
    pytest.importorskip("agents")
    from pay_safely.openai_agents import payment_guardrail, seller_check_tool

    tool = seller_check_tool(guard_with("allow"))
    assert tool.name == "check_seller_before_paying"
    rail = payment_guardrail(guard_with("block"), "url", "usd")

    class Ctx:
        tool_arguments = json.dumps({"url": "https://seller.example/p", "usd": 2})

    class Data:
        context = Ctx()
        agent = None

    import asyncio

    result = asyncio.run(rail.run(Data())) if hasattr(rail, "run") else rail.guardrail_function(Data())
    assert result.behavior["type"] == "reject_content"


def test_crewai_tool():
    pytest.importorskip("crewai")
    from pay_safely.crewai import SellerCheckTool

    tool = SellerCheckTool(guard=guard_with("block"))
    assert tool._run("https://seller.example/p", 1.0).startswith("Do not pay")


def test_agentkit_action_provider():
    pytest.importorskip("coinbase_agentkit")
    from pay_safely.agentkit import pay_safely_action_provider

    provider = pay_safely_action_provider(guard_with("allow"))
    actions = provider.get_actions(None)
    assert [a.name for a in actions] == ["pay_safely_check_seller_before_paying"] or actions[0].name.endswith("check_seller_before_paying")
    assert actions[0].invoke({"seller_url": "https://seller.example/p"}).startswith("Safe to pay")
