"""Keep passenger tickets aligned with trip status changes."""

from trips.models import TripStatus

from .models import Ticket, TicketStatus


def sync_tickets_for_trip(trip) -> int:
    """Expire or finalize tickets when a trip ends or is cancelled."""
    if trip.status == TripStatus.COMPLETED:
        updated = Ticket.objects.filter(
            trip=trip,
            status=TicketStatus.BOOKED,
        ).update(status=TicketStatus.USED)
        return updated

    if trip.status == TripStatus.CANCELLED:
        updated = Ticket.objects.filter(
            trip=trip,
            status__in=[TicketStatus.BOOKED, TicketStatus.RESERVED],
        ).update(status=TicketStatus.CANCELLED)
        return updated

    return 0


def is_ticket_expired(ticket) -> bool:
    trip_status = ticket.trip.status
    if trip_status in {TripStatus.CANCELLED, TripStatus.COMPLETED}:
        return True
    return ticket.status in {TicketStatus.USED, TicketStatus.CANCELLED}


def can_download_ticket(ticket) -> bool:
    if ticket.trip.status == TripStatus.CANCELLED:
        return False
    if ticket.status == TicketStatus.CANCELLED:
        return False
    if ticket.status == TicketStatus.RESERVED:
        return False
    return ticket.status in {TicketStatus.BOOKED, TicketStatus.USED}
