"""Core client: ask Screwtape.ai whether a seller is safe to pay, before your agent pays."""
from __future__ import annotations

import functools
import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

DEFAULT_BASE_URL = "https://screwtape.ai"
CHECK_PATH = "/v1/payment-check"

__all__ = [
    "PaySafely",
    "Verdict",
    "PaymentBlocked",
    "NeedsReview",
    "CheckUnavailable",
    "DailyLimitReached",
]


class PaySafelyError(Exception):
    """Base class for every error raised by this package."""


class PaymentBlocked(PaySafelyError):
    """The check said block. Do not pay."""

    def __init__(self, verdict: "Verdict"):
        self.verdict = verdict
        super().__init__("Payment blocked: " + "; ".join(verdict.reasons or ["seller failed the safety check"]))


class NeedsReview(PaySafelyError):
    """The check said review. A person should look before the agent pays."""

    def __init__(self, verdict: "Verdict"):
        self.verdict = verdict
        super().__init__("Payment needs review: " + "; ".join(verdict.reasons or ["the check could not confirm the seller"]))


class CheckUnavailable(PaySafelyError):
    """The check could not run (network error, timeout or server error). Fails closed by default."""


class DailyLimitReached(PaySafelyError):
    """The free daily calls are used and the request needs payment or an API key."""

    def __init__(self, message: str, body: Optional[Dict[str, Any]] = None):
        self.body = body or {}
        super().__init__(message)


@dataclass
class Verdict:
    """What the payment check returned."""

    verdict: str  # "allow", "review" or "block"
    reasons: List[str] = field(default_factory=list)
    payee: Optional[str] = None
    amount_usd: Optional[float] = None
    receipt_id: Optional[str] = None
    verify_url: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.verdict == "allow"

    @property
    def blocked(self) -> bool:
        return self.verdict == "block"

    @property
    def needs_review(self) -> bool:
        return self.verdict == "review"

    def summary(self) -> str:
        why = "; ".join(self.reasons) if self.reasons else "no reasons given"
        rid = f" Receipt: {self.receipt_id}." if self.receipt_id else ""
        return f"{self.verdict.upper()}: {why}.{rid}"

    @classmethod
    def from_response(cls, body: Dict[str, Any]) -> "Verdict":
        return cls(
            verdict=str(body.get("verdict", "review")),
            reasons=[str(r) for r in body.get("reasons", []) or []],
            payee=body.get("payee"),
            amount_usd=body.get("amount_usd"),
            receipt_id=body.get("receipt_id"),
            verify_url=body.get("verify_url"),
            raw=body,
        )


# A transport takes (url, json_body, headers, timeout) and returns (status_code, parsed_json_or_text).
Transport = Callable[[str, Dict[str, Any], Dict[str, str], float], "tuple[int, Any]"]


def _urllib_transport(url: str, body: Dict[str, Any], headers: Dict[str, str], timeout: float):
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - https URL, fixed endpoint
            payload = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as err:
        payload = err.read().decode("utf-8", "replace")
        status = err.code
    try:
        return status, json.loads(payload)
    except ValueError:
        return status, payload


class PaySafely:
    """Ask Screwtape.ai whether a seller is safe to pay.

    Parameters
    ----------
    api_key:
        Optional free API key (10 checks a day). Without a key you get 3 free checks a day.
    agent_id:
        A label for your agent. It shows up on the signed receipt.
    fail_open:
        If True, a failed check (network error, timeout) lets the payment go ahead. Default False:
        if the check cannot run, the payment is not allowed.
    allow_review:
        If True, a "review" verdict is treated as allowed. Default False: "review" stops the payment
        until a person looks.
    transport:
        Advanced. A function that sends the request, so you can use your own HTTP client, for example
        one that can attach a payment when the free checks run out.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        agent_id: str = "pay-safely",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        fail_open: bool = False,
        allow_review: bool = False,
        transport: Optional[Transport] = None,
    ):
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.fail_open = fail_open
        self.allow_review = allow_review
        self._transport = transport or _urllib_transport

    # -- checking ---------------------------------------------------------------------------------

    def check(
        self,
        seller_url: Optional[str] = None,
        amount: Optional[float] = None,
        payment_required: Optional[Any] = None,
    ) -> Verdict:
        """Run the check and return the Verdict. Raises CheckUnavailable or DailyLimitReached on failure.

        seller_url: the public https URL of the seller or paid endpoint you are about to pay.
        amount: the amount in US dollars your agent intends to pay (lets the check flag an over-price).
        payment_required: alternatively, the seller's payment-required response, if you already have it.
        """
        if not seller_url and payment_required is None:
            raise ValueError("Give seller_url or payment_required.")
        body: Dict[str, Any] = {"agent_id": self.agent_id, "event_id": f"{self.agent_id}-{uuid.uuid4().hex[:16]}"}
        if seller_url:
            body["seller_url"] = seller_url
        if payment_required is not None:
            body["payment_required"] = payment_required
        if amount is not None:
            body["intended_amount"] = float(amount)
        headers = {"content-type": "application/json", "accept": "application/json", "user-agent": "screwtape-pay-safely/0.2"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        try:
            status, payload = self._transport(self.base_url + CHECK_PATH, body, headers, self.timeout)
        except PaySafelyError:
            raise
        except Exception as err:  # network error, timeout, TLS
            raise CheckUnavailable(f"Could not reach the check: {err.__class__.__name__}") from err
        if status == 200 and isinstance(payload, dict):
            return Verdict.from_response(payload)
        if status == 402:
            detail = payload if isinstance(payload, dict) else {}
            hint = detail.get("next_action") or "The free daily checks are used."
            raise DailyLimitReached(
                f"{hint} Get a free key at {self.base_url}/v1/signup (10 checks a day), or see {self.base_url}/llms.txt for pay-per-call.",
                detail,
            )
        if status == 429:
            raise CheckUnavailable("Rate limited. Wait a moment and retry.")
        if status == 400:
            message = payload.get("message") if isinstance(payload, dict) else str(payload)
            raise ValueError(f"The check rejected the input: {message}")
        raise CheckUnavailable(f"The check returned HTTP {status}.")

    def require_safe(
        self,
        seller_url: Optional[str] = None,
        amount: Optional[float] = None,
        payment_required: Optional[Any] = None,
    ) -> Verdict:
        """Like check(), but raises PaymentBlocked or NeedsReview unless the seller is allowed.

        Call this right before your agent pays. If it returns, it is safe to go ahead.
        """
        try:
            verdict = self.check(seller_url=seller_url, amount=amount, payment_required=payment_required)
        except (CheckUnavailable, DailyLimitReached):
            if self.fail_open:
                return Verdict(verdict="allow", reasons=["The check was unavailable and fail_open is on."])
            raise
        if verdict.blocked:
            raise PaymentBlocked(verdict)
        if verdict.needs_review and not self.allow_review:
            raise NeedsReview(verdict)
        return verdict

    # -- wrapping ---------------------------------------------------------------------------------

    def protect(
        self,
        seller_url: Callable[..., Optional[str]],
        amount: Optional[Callable[..., Optional[float]]] = None,
    ):
        """Decorator: run the check on the arguments of a payment function before it runs.

            @guard.protect(seller_url=lambda url, usd: url, amount=lambda url, usd: usd)
            def pay(url, usd): ...
        """

        def decorate(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                self.require_safe(seller_url=seller_url(*args, **kwargs), amount=amount(*args, **kwargs) if amount else None)
                return func(*args, **kwargs)

            return wrapper

        return decorate
