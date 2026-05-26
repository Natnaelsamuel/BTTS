"""Generate passenger digital ticket PDFs."""

from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import TicketStatus
from .ticket_lifecycle import can_download_ticket, is_ticket_expired

BRAND = colors.HexColor("#1F4D3A")
BRAND_LIGHT = colors.HexColor("#E8F6EE")
MUTED = colors.HexColor("#5C6F66")
INK = colors.HexColor("#102820")
WARN = colors.HexColor("#C62828")
WARN_BG = colors.HexColor("#FDECEC")


def _payment_label(ticket) -> str:
    payment = getattr(ticket, "payment", None)
    if payment is None:
        return "—"
    return (payment.status or "—").replace("_", " ").title()


def _fare_label(ticket) -> str:
    fare = ticket.fare_amount if ticket.fare_amount is not None else ticket.trip.fare
    if fare is None:
        return "—"
    return f"ETB {fare:,.2f}"


def _status_banner_text(ticket) -> str | None:
    if is_ticket_expired(ticket):
        if ticket.trip.status == "CANCELLED":
            return "EXPIRED — TRIP CANCELLED"
        if ticket.trip.status == "COMPLETED":
            return "EXPIRED — TRIP COMPLETED"
        return "EXPIRED"
    if ticket.status == TicketStatus.BOOKED:
        return "VALID — PRESENT AT BOARDING"
    if ticket.status == TicketStatus.USED:
        return "USED — TRIP COMPLETED"
    return None


def build_ticket_pdf(ticket) -> bytes:
    buffer = BytesIO()
    page_width, page_height = A4
    margin = 16 * mm
    card_width = page_width - (margin * 2)
    card_height = 132 * mm
    card_bottom = page_height - margin - 28 * mm - card_height
    card_top = card_bottom + card_height

    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Zemen Bus Ticket {ticket.id}")

    passenger_name = ticket.user.get_full_name() or ticket.user.email or ticket.user.username
    origin = ticket.trip.route.origin
    destination = ticket.trip.route.destination
    departure = ticket.trip.departure_time
    arrival = ticket.trip.arrival_time
    driver_name = ticket.trip.driver.get_full_name() or ticket.trip.driver.username
    seat = str(ticket.seat.seat_number)
    bus_plate = ticket.trip.bus.plate_number
    bus_capacity = ticket.trip.bus.capacity

    # Drop shadow
    pdf.setFillColor(colors.HexColor("#D4E4DC"))
    pdf.roundRect(margin + 2.5, card_bottom - 2.5, card_width, card_height, 12, fill=1, stroke=0)

    # Card shell
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(BRAND)
    pdf.setLineWidth(1.4)
    pdf.roundRect(margin, card_bottom, card_width, card_height, 12, fill=1, stroke=1)

    # Header band
    header_h = 24 * mm
    pdf.setFillColor(BRAND)
    pdf.roundRect(margin, card_top - header_h, card_width, header_h, 12, fill=1, stroke=0)
    pdf.rect(margin, card_top - header_h, card_width, header_h / 2, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(margin + 10 * mm, card_top - 14 * mm, "Zemen Bus")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(margin + card_width - 10 * mm, card_top - 11 * mm, "DIGITAL BOARDING PASS")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(
        margin + card_width - 10 * mm,
        card_top - 17 * mm,
        (ticket.status or "—").replace("_", " ").upper(),
    )

    y = card_top - header_h - 8 * mm

    # Route block
    pdf.setFillColor(BRAND_LIGHT)
    pdf.setStrokeColor(colors.HexColor("#B8D4C4"))
    pdf.roundRect(margin + 8 * mm, y - 18 * mm, card_width - 16 * mm, 18 * mm, 6, fill=1, stroke=1)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin + 12 * mm, y - 5 * mm, "ROUTE")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(margin + 12 * mm, y - 13 * mm, f"{origin}  →  {destination}")
    y -= 24 * mm

    # Large seat highlight
    seat_box_w = 42 * mm
    seat_box_h = 28 * mm
    pdf.setFillColor(BRAND)
    pdf.roundRect(margin + 8 * mm, y - seat_box_h, seat_box_w, seat_box_h, 8, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin + 12 * mm, y - 7 * mm, "SEAT")
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(margin + 12 * mm, y - 22 * mm, seat)

    info_x = margin + 8 * mm + seat_box_w + 6 * mm
    info_w = card_width - 16 * mm - seat_box_w - 6 * mm

    def info_row(label: str, value: str, row_y: float, bold: bool = False) -> None:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(info_x, row_y, label)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if bold else 9)
        # Truncate long values
        max_chars = int(info_w / (4.2 if bold else 3.8))
        display = value if len(value) <= max_chars else value[: max_chars - 1] + "…"
        pdf.drawString(info_x, row_y - 4.5 * mm, display)

    info_row("PASSENGER", passenger_name, y - 2 * mm, bold=True)
    info_row("BUS", f"{bus_plate} · {bus_capacity} seats", y - 11 * mm)
    info_row("DRIVER", driver_name, y - 20 * mm)
    y -= seat_box_h + 6 * mm

    # Dashed line
    pdf.setStrokeColor(colors.HexColor("#B8C9BF"))
    pdf.setDash(4, 3)
    pdf.line(margin + 8 * mm, y, margin + card_width - 8 * mm, y)
    pdf.setDash()
    y -= 6 * mm

    col_mid = margin + card_width / 2

    def grid_field(label: str, value: str, x: float, row_y: float) -> None:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(x, row_y, label)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, row_y - 5 * mm, value)

    grid_field("DEPARTURE", departure.strftime("%a, %d %b %Y"), margin + 8 * mm, y)
    grid_field("DEPART TIME", departure.strftime("%H:%M"), col_mid, y)
    y -= 14 * mm
    arr_date = arrival.strftime("%a, %d %b %Y") if arrival else "—"
    arr_time = arrival.strftime("%H:%M") if arrival else "—"
    grid_field("ARRIVAL", arr_date, margin + 8 * mm, y)
    grid_field("ARRIVE TIME", arr_time, col_mid, y)
    y -= 14 * mm
    grid_field("FARE", _fare_label(ticket), margin + 8 * mm, y)
    grid_field("PAYMENT", _payment_label(ticket), col_mid, y)
    y -= 14 * mm

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(margin + 8 * mm, y, "TICKET ID")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin + 8 * mm, y - 4.5 * mm, str(ticket.id))

    # Status banner at bottom of card
    banner = _status_banner_text(ticket)
    if banner:
        banner_y = card_bottom + 8 * mm
        expired = is_ticket_expired(ticket) and ticket.status != TicketStatus.USED
        if expired:
            pdf.setFillColor(WARN_BG)
            pdf.setStrokeColor(WARN)
        else:
            pdf.setFillColor(BRAND_LIGHT)
            pdf.setStrokeColor(BRAND)
        pdf.roundRect(margin + 8 * mm, banner_y, card_width - 16 * mm, 9 * mm, 4, fill=1, stroke=1)
        pdf.setFillColor(WARN if expired else BRAND)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(margin + card_width / 2, banner_y + 3 * mm, banner)

    # Footer
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(
        page_width / 2,
        margin + 4 * mm,
        f"Generated {timezone.now().strftime('%d %b %Y %H:%M')} · Bus Tracking & Ticketing System · Ethiopia",
    )
    pdf.drawCentredString(
        page_width / 2,
        margin,
        "Arrive at least 15 minutes before departure. Show this ticket at boarding.",
    )

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def ticket_pdf_response(ticket):
    from django.http import HttpResponse

    if not can_download_ticket(ticket) and ticket.status != TicketStatus.USED:
        raise ValueError("This ticket is no longer available for download.")

    pdf_bytes = build_ticket_pdf(ticket)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="zemenbus-ticket-{ticket.id}.pdf"'
    return response
