"""Admin analytics aggregation and CSV export helpers."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from buses.models import Bus
from feedback.models import Feedback
from feedback.serializers import FeedbackSerializer
from routes.models import Route
from trips.models import Trip, TripStatus
from users.models import User, UserRole

from .models import PaymentStatus, Ticket, TicketStatus


def _decimal_str(value) -> str:
    if value is None:
        return "0.00"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def _fill_daily_series(
    start_day: date,
    end_day: date,
    rows: list[dict],
) -> list[dict]:
    by_date = {row["date"]: row for row in rows}
    filled: list[dict] = []
    current = start_day
    while current <= end_day:
        key = current.isoformat()
        if key in by_date:
            filled.append(by_date[key])
        else:
            filled.append({"date": key, "count": 0, "revenue": "0.00"})
        current += timedelta(days=1)
    return filled


def build_analytics_report(days: int = 30) -> dict:
    days = max(1, min(days, 365))
    end = timezone.now()
    start = end - timedelta(days=days)
    start_day = start.date()
    end_day = end.date()

    tickets_qs = Ticket.objects.filter(booked_at__gte=start).select_related(
        "trip", "trip__route", "payment"
    )

    tickets_by_day_qs = (
        tickets_qs.annotate(day=TruncDate("booked_at"))
        .values("day")
        .annotate(
            count=Count("id"),
            revenue=Coalesce(
                Sum(
                    "payment__amount",
                    filter=Q(payment__status=PaymentStatus.PAID),
                ),
                Decimal("0"),
            ),
        )
        .order_by("day")
    )
    tickets_per_day = [
        {
            "date": row["day"].isoformat(),
            "count": row["count"],
            "revenue": _decimal_str(row["revenue"]),
        }
        for row in tickets_by_day_qs
    ]
    tickets_per_day = _fill_daily_series(start_day, end_day, tickets_per_day)

    tickets_by_status = {
        row["status"]: row["count"]
        for row in tickets_qs.values("status").annotate(count=Count("id"))
    }

    payments_by_status = {
        row["payment__status"]: row["count"]
        for row in tickets_qs.filter(payment__isnull=False)
        .values("payment__status")
        .annotate(count=Count("id"))
        if row["payment__status"]
    }

    top_routes_qs = (
        tickets_qs.values(
            "trip__route__origin",
            "trip__route__destination",
        )
        .annotate(
            bookings=Count("id"),
            revenue=Coalesce(
                Sum(
                    "payment__amount",
                    filter=Q(payment__status=PaymentStatus.PAID),
                ),
                Decimal("0"),
            ),
        )
        .order_by("-bookings")[:8]
    )
    top_routes = [
        {
            "origin": row["trip__route__origin"],
            "destination": row["trip__route__destination"],
            "label": f"{row['trip__route__origin']} → {row['trip__route__destination']}",
            "bookings": row["bookings"],
            "revenue": _decimal_str(row["revenue"]),
        }
        for row in top_routes_qs
    ]

    trip_status_counts = {
        row["status"]: row["count"]
        for row in Trip.objects.filter(departure_time__gte=start)
        .values("status")
        .annotate(count=Count("id"))
    }

    total_revenue = tickets_qs.filter(
        payment__status=PaymentStatus.PAID
    ).aggregate(total=Coalesce(Sum("payment__amount"), Decimal("0")))["total"]

    sold_statuses = [TicketStatus.BOOKED, TicketStatus.USED]
    tickets_sold = tickets_qs.filter(status__in=sold_statuses).count()
    cancelled = tickets_qs.filter(status=TicketStatus.CANCELLED).count()
    reserved = tickets_qs.filter(status=TicketStatus.RESERVED).count()
    total_ticket_actions = tickets_qs.count()
    cancellation_rate = (
        round((cancelled / total_ticket_actions) * 100, 1)
        if total_ticket_actions
        else 0.0
    )

    trips_in_period = Trip.objects.filter(
        departure_time__gte=start,
        departure_time__lte=end,
    ).select_related("bus")
    total_capacity = sum(trip.bus.capacity for trip in trips_in_period)
    occupied_seats = tickets_qs.filter(
        status__in=sold_statuses,
        trip__in=trips_in_period,
    ).count()
    occupancy_rate = (
        round((occupied_seats / total_capacity) * 100, 1)
        if total_capacity
        else 0.0
    )

    feedback_counts = {
        row["category"]: row["count"]
        for row in Feedback.objects.filter(created_at__gte=start)
        .values("category")
        .annotate(count=Count("id"))
    }

    recent_feedback = FeedbackSerializer(
        Feedback.objects.select_related("user")
        .filter(created_at__gte=start)
        .order_by("-created_at")[:6],
        many=True,
    ).data

    users_by_role = {
        row["role"]: row["count"]
        for row in User.objects.values("role").annotate(count=Count("id"))
    }

    return {
        "period": {
            "days": days,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "summary": {
            "total_revenue": _decimal_str(total_revenue),
            "tickets_sold": tickets_sold,
            "tickets_reserved": reserved,
            "tickets_cancelled": cancelled,
            "cancellation_rate": cancellation_rate,
            "occupancy_rate": occupancy_rate,
            "total_buses": Bus.objects.count(),
            "total_routes": Route.objects.count(),
            "trips_in_period": trips_in_period.count(),
            "scheduled_trips": trip_status_counts.get(TripStatus.SCHEDULED, 0),
            "in_progress_trips": trip_status_counts.get(TripStatus.IN_PROGRESS, 0),
            "completed_trips": trip_status_counts.get(TripStatus.COMPLETED, 0),
            "passengers": users_by_role.get(UserRole.PASSENGER, 0),
            "drivers": users_by_role.get(UserRole.DRIVER, 0),
            "admins": users_by_role.get(UserRole.ADMIN, 0),
        },
        "tickets_per_day": tickets_per_day,
        "tickets_by_status": tickets_by_status,
        "payments_by_status": payments_by_status,
        "trip_status_counts": trip_status_counts,
        "top_routes": top_routes,
        "users_by_role": users_by_role,
        "feedback_by_category": feedback_counts,
        "recent_feedback": recent_feedback,
    }


def build_analytics_csv(report: dict, report_type: str = "full") -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    period = report["period"]
    summary = report["summary"]

    writer.writerow(["BTTS Analytics Report"])
    writer.writerow(["Generated", timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC")])
    writer.writerow(["Period (days)", period["days"]])
    writer.writerow(["From", period["start"]])
    writer.writerow(["To", period["end"]])
    writer.writerow([])

    if report_type in ("full", "summary"):
        writer.writerow(["SUMMARY"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total revenue (ETB)", summary["total_revenue"]])
        writer.writerow(["Tickets sold", summary["tickets_sold"]])
        writer.writerow(["Tickets reserved", summary["tickets_reserved"]])
        writer.writerow(["Tickets cancelled", summary["tickets_cancelled"]])
        writer.writerow(["Cancellation rate (%)", summary["cancellation_rate"]])
        writer.writerow(["Occupancy rate (%)", summary["occupancy_rate"]])
        writer.writerow(["Total buses", summary["total_buses"]])
        writer.writerow(["Total routes", summary["total_routes"]])
        writer.writerow(["Trips in period", summary["trips_in_period"]])
        writer.writerow(["Passengers", summary["passengers"]])
        writer.writerow(["Drivers", summary["drivers"]])
        writer.writerow([])

    if report_type in ("full", "revenue", "tickets"):
        writer.writerow(["DAILY TICKETS AND REVENUE"])
        writer.writerow(["Date", "Tickets", "Revenue (ETB)"])
        for row in report["tickets_per_day"]:
            writer.writerow([row["date"], row["count"], row["revenue"]])
        writer.writerow([])

    if report_type in ("full", "routes"):
        writer.writerow(["TOP ROUTES"])
        writer.writerow(["Route", "Bookings", "Revenue (ETB)"])
        for row in report["top_routes"]:
            writer.writerow([row["label"], row["bookings"], row["revenue"]])
        writer.writerow([])

    if report_type in ("full", "status"):
        writer.writerow(["TICKETS BY STATUS"])
        writer.writerow(["Status", "Count"])
        for status, count in report["tickets_by_status"].items():
            writer.writerow([status, count])
        writer.writerow([])

        writer.writerow(["PAYMENTS BY STATUS"])
        writer.writerow(["Status", "Count"])
        for status, count in report["payments_by_status"].items():
            writer.writerow([status, count])
        writer.writerow([])

        writer.writerow(["TRIPS BY STATUS (departures in period)"])
        writer.writerow(["Status", "Count"])
        for status, count in report["trip_status_counts"].items():
            writer.writerow([status, count])
        writer.writerow([])

        writer.writerow(["FEEDBACK BY CATEGORY (period)"])
        writer.writerow(["Category", "Count"])
        for category, count in report["feedback_by_category"].items():
            writer.writerow([category, count])

    return buffer.getvalue()
