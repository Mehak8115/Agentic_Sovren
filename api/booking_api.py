# api/booking_api.py

from fastapi import APIRouter, Query
from enum import Enum
from agents.booking_agent import BookingAgent

router = APIRouter()
agent  = BookingAgent()


class PaymentMethod(str, Enum):
    online = "online"
    upi    = "upi"
    card   = "card"
    cash   = "cash"


@router.post(
    "/booking/run",
    tags=["Booking Agent"],
    summary="Run Booking Agent",
)
def run_booking_agent(
    query: str = Query(
        ...,
        description="Natural language booking query",
        examples="Suggest luxury boats in Goa for 20 people under 50k in July",
    ),
    user_name: str = Query(
        default="Guest",
        description="Your name",
        examples="Rahul",
    ),
    confirm_booking: bool = Query(
        default=False,
        description="Confirm and process booking",
    ),
    payment_method: PaymentMethod = Query(
        default=PaymentMethod.online,
        description="Payment method",
    ),
    include_thought_process: bool = Query(
        default=False,
        description="Include agent reasoning in response",
    ),
):
    return agent.run(
        query=query,
        user_name=user_name,
        confirm_booking_override=confirm_booking,
        payment_method_override=payment_method.value,
        include_thought_process=include_thought_process,
    )
