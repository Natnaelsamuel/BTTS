from django.utils import timezone

from .models import PaymentStatus, TicketStatus


def finalize_payment_from_verify(payment, verify_response):
    data = verify_response.get("data", {})
    status_value = str(data.get("status") or verify_response.get("status") or "").lower()

    if status_value == "success":
        payment.status = PaymentStatus.PAID
        payment.paid_at = timezone.now()
        payment.raw_response = verify_response
        payment.save(update_fields=["status", "paid_at", "raw_response", "updated_at"])

        ticket = payment.ticket
        ticket.status = TicketStatus.BOOKED
        ticket.save(update_fields=["status", "updated_at"])
        return "paid"

    if status_value in {"pending", "processing"}:
        payment.status = PaymentStatus.PENDING
        payment.raw_response = verify_response
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        return "pending"

    payment.status = PaymentStatus.FAILED
    payment.raw_response = verify_response
    payment.save(update_fields=["status", "raw_response", "updated_at"])

    ticket = payment.ticket
    ticket.status = TicketStatus.CANCELLED
    ticket.save(update_fields=["status", "updated_at"])
    return "failed"