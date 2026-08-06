from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas.billing import CheckoutRequest, CheckoutResponse

router = APIRouter(tags=["billing"])


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(payload: CheckoutRequest) -> CheckoutResponse:
    not_implemented("§1.5 Payment Integration")


@router.post("/payments/webhook")
async def payment_webhook() -> dict:
    # Non-negotiable per CLAUDE.md: validate signature FIRST, then idempotency check,
    # before any DB write. Stubbed until §1.5 builds both checks — do not add DB/queue
    # side effects here ahead of that.
    not_implemented("§1.5 Payment Integration")
