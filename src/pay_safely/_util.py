from __future__ import annotations

from typing import Optional

from .core import CheckUnavailable, DailyLimitReached, NeedsReview, PaymentBlocked, PaySafely


def run_check_text(guard: PaySafely, seller_url: Optional[str], amount: Optional[float]) -> "tuple[bool, str]":
    """Run the guard and return (ok_to_pay, message the agent can read)."""
    try:
        verdict = guard.require_safe(seller_url=seller_url, amount=amount)
    except PaymentBlocked as err:
        return False, f"Do not pay. {err.verdict.summary()}"
    except NeedsReview as err:
        return False, f"Do not pay yet; ask a person to review. {err.verdict.summary()}"
    except (CheckUnavailable, DailyLimitReached) as err:
        return False, f"Do not pay: the seller check could not run. {err}"
    except ValueError as err:
        return False, f"Do not pay: {err}"
    return True, f"Safe to pay. {verdict.summary()}"
