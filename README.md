# pay-safely

Check that a seller is safe to pay **before your AI agent pays**.

`pay-safely` asks [Screwtape.ai](https://screwtape.ai) one question at the moment your agent is about to pay: *is this seller safe to pay?* You get back **allow**, **review** or **block**, with reasons and a signed receipt you can verify later.

It has no required dependencies and drops into LangChain, LangGraph, CrewAI, the OpenAI Agents SDK, AgentKit, Haystack, Pydantic AI, LlamaIndex and Agno.

## What the check looks at

- The price and payee the seller asks for, compared with what the seller has published.
- The payee against a denylist and a sanctions list.
- Whether the amount is far above what your agent intended to pay.
- Whether the same payment was already made.
- Whether the seller URL answers with a valid payment request.

If the check cannot confirm something, it says **review**, not **allow**. If it cannot run at all (network error, timeout), this package stops the payment by default.

## Install

```bash
pip install screwtape-pay-safely
# plus the extra for your framework:
pip install "screwtape-pay-safely[langchain]"      # LangChain and LangGraph
pip install "screwtape-pay-safely[crewai]"
pip install "screwtape-pay-safely[openai-agents]"
pip install "screwtape-pay-safely[agentkit]"
pip install "screwtape-pay-safely[haystack]"
pip install "screwtape-pay-safely[pydantic-ai]"
pip install "screwtape-pay-safely[llama-index]"
pip install "screwtape-pay-safely[agno]"
```

## Use it in plain Python

```python
from pay_safely import PaySafely, PaymentBlocked, NeedsReview

guard = PaySafely(agent_id="my-agent")          # 3 free checks a day, no key

try:
    verdict = guard.require_safe("https://seller.example/pay", amount=0.05)
except PaymentBlocked as err:
    print("Do not pay:", err)
except NeedsReview as err:
    print("Ask a person first:", err)
else:
    print("OK to pay. Receipt:", verdict.receipt_id)
    # ... make your payment here ...
```

Or wrap your payment function:

```python
@guard.protect(seller_url=lambda url, usd: url, amount=lambda url, usd: usd)
def pay(url, usd):
    ...
```

## LangChain and LangGraph

```python
from pay_safely import PaySafely
from pay_safely.langchain import seller_check_tool, guard_tool

guard = PaySafely(agent_id="my-agent")
tools = [
    seller_check_tool(guard),                                      # the agent can ask "is this seller safe?"
    guard_tool(my_payment_tool, guard, seller_url_arg="url", amount_arg="usd"),  # runs only on allow
]
```

## CrewAI

```python
from pay_safely import PaySafely
from pay_safely.crewai import SellerCheckTool

buyer = Agent(role="Buyer", goal="Buy safely", backstory="...", tools=[SellerCheckTool(guard=PaySafely(agent_id="buyer"))])
```

## OpenAI Agents SDK

```python
from agents import Agent, function_tool
from pay_safely import PaySafely
from pay_safely.openai_agents import seller_check_tool, payment_guardrail

guard = PaySafely(agent_id="buyer")
pay = function_tool(pay_seller, tool_input_guardrails=[payment_guardrail(guard, "url", "usd")])
agent = Agent(name="Buyer", tools=[seller_check_tool(guard), pay])
```

## AgentKit

```python
from pay_safely import PaySafely
from pay_safely.agentkit import pay_safely_action_provider

# add to the action_providers list in your AgentKit config
provider = pay_safely_action_provider(PaySafely(agent_id="buyer"))
```

## Haystack

```python
from pay_safely import PaySafely
from pay_safely.haystack import SellerCheck

check = SellerCheck(guard=PaySafely(agent_id="buyer"))
print(check.run(seller_url="https://seller.example/pay", amount_usd=0.05)["result"])
```

## Pydantic AI

```python
from pydantic_ai import Agent
from pay_safely import PaySafely
from pay_safely.pydantic_ai import seller_check_capability

agent = Agent("openai:gpt-4o", capabilities=[seller_check_capability(PaySafely(agent_id="buyer"))])
```

## LlamaIndex

```python
from pay_safely import PaySafely
from pay_safely.llama_index import seller_check_tool

tools = [seller_check_tool(PaySafely(agent_id="buyer"))]
```

## Agno

```python
from agno.agent import Agent
from pay_safely import PaySafely
from pay_safely.agno import SellerCheckTools

agent = Agent(tools=[SellerCheckTools(guard=PaySafely(agent_id="buyer"))])
```

## Free checks, keys and paid use

| | Checks |
|---|---|
| No key | 3 free a day |
| Free API key | 10 free a day. Get one at <https://screwtape.ai/v1/signup> and pass `PaySafely(api_key="...")` |
| After that | $0.005 per check. See <https://screwtape.ai/llms.txt> for how an agent pays per call. Pass your own payment-capable HTTP client with `transport=` |

When the free checks run out, `check()` raises `DailyLimitReached` with the link to get a free key.

## Options

| Option | Default | Meaning |
|---|---|---|
| `fail_open` | `False` | If `True`, a check that cannot run lets the payment go ahead. |
| `allow_review` | `False` | If `True`, a **review** verdict does not stop the payment. |
| `timeout` | `10.0` | Seconds to wait for the check. |
| `transport` | built in | Your own function to send the request. |

## Limits

This is a second opinion, not a guarantee. The check advises and records. Your code decides whether to pay, and the check cannot stop a payment your code makes anyway. It does not hold funds.

## Verify a receipt

Every answer includes a `receipt_id` and `verify_url`. Verify it for free at <https://screwtape.ai/verify/>.

## Develop

```bash
pip install -e ".[test]"
pytest
```

## Support

support@screwtape.ai · <https://screwtape.ai>

MIT license.
