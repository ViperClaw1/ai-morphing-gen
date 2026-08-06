class AppError(Exception):
    """Raise for any expected API failure. Caught by the handler in app/main.py and
    rendered as {"error": str, "code": str} — the shape .claude/rules/api-conventions.md
    mandates for every backend error response. Never let a raw HTTPException or unhandled
    exception reach the client (that would leak FastAPI's default {"detail": ...} shape
    or a stack trace instead).
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)
