import pytest

from pay_safely import CheckUnavailable, DailyLimitReached, NeedsReview, PaymentBlocked, PaySafely


def fake(status, payload, seen=None):
    def transport(url, body, headers, timeout):
        if seen is not None:
            seen.append((url, body, headers))
        return status, payload

    return transport


def test_allow_returns_verdict_and_sends_expected_request():
    seen = []
    guard = PaySafely(api_key="k", agent_id="a1", transport=fake(200, {"verdict": "allow", "reasons": ["ok"], "receipt_id": "r1"}, seen))
    verdict = guard.require_safe("https://seller.example/pay", amount=0.05)
    assert verdict.allowed and verdict.receipt_id == "r1"
    url, body, headers = seen[0]
    assert url == "https://screwtape.ai/v1/payment-check"
    assert body["seller_url"] == "https://seller.example/pay" and body["intended_amount"] == 0.05 and body["agent_id"] == "a1"
    assert headers["authorization"] == "Bearer k"


def test_block_raises():
    guard = PaySafely(transport=fake(200, {"verdict": "block", "reasons": ["payee is sanctioned"]}))
    with pytest.raises(PaymentBlocked) as err:
        guard.require_safe("https://seller.example/pay")
    assert "sanctioned" in str(err.value)


def test_review_stops_unless_allowed():
    payload = {"verdict": "review", "reasons": ["could not fetch"]}
    with pytest.raises(NeedsReview):
        PaySafely(transport=fake(200, payload)).require_safe("https://seller.example/pay")
    assert PaySafely(transport=fake(200, payload), allow_review=True).require_safe("https://seller.example/pay").needs_review


def test_fails_closed_by_default_and_open_on_request():
    def boom(*a):
        raise TimeoutError("slow")

    with pytest.raises(CheckUnavailable):
        PaySafely(transport=boom).require_safe("https://seller.example/pay")
    assert PaySafely(transport=boom, fail_open=True).require_safe("https://seller.example/pay").allowed


def test_daily_limit_message_points_to_free_key():
    guard = PaySafely(transport=fake(402, {"next_action": "Free calls used."}))
    with pytest.raises(DailyLimitReached) as err:
        guard.check("https://seller.example/pay")
    assert "signup" in str(err.value)


def test_bad_input():
    with pytest.raises(ValueError):
        PaySafely(transport=fake(200, {})).check()
    with pytest.raises(ValueError):
        PaySafely(transport=fake(400, {"message": "seller_url must be a public https URL."})).check("http://x")


def test_protect_decorator_blocks_payment_function():
    paid = []
    guard = PaySafely(transport=fake(200, {"verdict": "block", "reasons": ["no"]}))

    @guard.protect(seller_url=lambda url, usd: url, amount=lambda url, usd: usd)
    def pay(url, usd):
        paid.append(url)

    with pytest.raises(PaymentBlocked):
        pay("https://seller.example/pay", 1.0)
    assert paid == []
