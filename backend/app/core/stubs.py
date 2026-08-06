from app.core.errors import AppError


def not_implemented(phase: str) -> None:
    """Marks a route as scaffolded but not yet built. Raising a typed 501 instead of
    returning fake 200 data makes stub endpoints fail loudly against real clients and
    keeps the API contract (schemas/status codes) reviewable ahead of the logic landing.
    """
    raise AppError(
        status_code=501,
        code="NOT_IMPLEMENTED",
        message=f"Not implemented yet — see docs/implementation_plan.md {phase}",
    )
