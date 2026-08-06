from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    project_id: str


class CheckoutResponse(BaseModel):
    checkout_url: str
