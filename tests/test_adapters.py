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


def test_haystack_component():
    pytest.importorskip("haystack")
    from pay_safely.haystack import SellerCheck

    blocked = SellerCheck(guard=guard_with("block")).run("https://seller.example/p", 1.0)
    assert blocked["result"].startswith("Do not pay")
    allowed = SellerCheck(guard=guard_with("allow")).run("https://seller.example/p", 1.0)
    assert allowed["result"].startswith("Safe to pay")


def test_pydantic_ai_capability():
    pytest.importorskip("pydantic_ai")
    from pay_safely.pydantic_ai import seller_check_capability

    cap = seller_check_capability(guard_with("allow"))
    assert cap.id == "paysafely-seller-check"
    # Resolve the registered tool and call it.
    toolset = cap.get_toolset() if hasattr(cap, "get_toolset") else None
    called = False
    if toolset is not None and hasattr(toolset, "tools"):
        tools = toolset.tools
        if isinstance(tools, dict):
            tools = list(tools.values())
        for tool in tools or []:
            fn = getattr(tool, "function", None) or getattr(tool, "fn", None) or getattr(tool, "call", None)
            if callable(fn):
                result = fn(seller_url="https://seller.example/p", amount_usd=1.0)
                assert str(result).startswith("Safe to pay")
                called = True
                break
    if not called:
        # Fallback: walk capability attributes for the wrapped function.
        for name in dir(cap):
            if name.startswith("_"):
                continue
            obj = getattr(cap, name)
            if callable(obj) and getattr(obj, "__name__", "") == "check_seller_before_paying":
                assert obj("https://seller.example/p", 1.0).startswith("Safe to pay")
                called = True
                break
    assert called, "could not invoke the Pydantic AI seller-check tool"


def test_llama_index_tool():
    pytest.importorskip("llama_index.core")
    from pay_safely.llama_index import seller_check_tool

    tool = seller_check_tool(guard_with("allow"))
    assert tool.metadata.name == "check_seller_before_paying"
    result = tool.call(seller_url="https://seller.example/p", amount_usd=1.0)
    text = result if isinstance(result, str) else getattr(result, "content", None) or str(result)
    assert "Safe to pay" in text


def test_agno_toolkit():
    pytest.importorskip("agno")
    from pay_safely.agno import SellerCheckTools

    tools = SellerCheckTools(guard=guard_with("block"))
    assert tools.check_seller_before_paying("https://seller.example/p", 1.0).startswith("Do not pay")
    assert "check_seller_before_paying" in getattr(tools, "functions", {}) or tools.name == "paysafely_seller_check"
