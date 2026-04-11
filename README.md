## BTTS Backend

Backend for the Bus Tracking and Ticketing System built with Django, Django REST Framework, JWT auth, and PostgreSQL.

## Current Status

Implemented through Step 6:

1. Project setup, auth base, Swagger docs
2. Core domain models and constraints
3. JWT auth with role-based permissions
4. Core admin, passenger, and driver APIs
5. Booking logic and seat availability behavior
6. Simulated trip tracking APIs

## Tech Stack

- Django
- Django REST Framework
- SimpleJWT
- drf-spectacular (OpenAPI/Swagger)
- PostgreSQL

## Project Apps

- `users` - custom user model, roles, auth, user listing/search
- `buses` - bus management, seats, seat availability endpoint
- `routes` - route management
- `trips` - trip management, assignment, driver status updates
- `tickets` - booking and cancellation flow
- `tracking` - trip location updates and current location lookup

## Roles

- `ADMIN`
- `PASSENGER`
- `DRIVER`

## Setup

1. Copy `.env.example` to `.env` and set DB credentials.
2. Ensure PostgreSQL is running and database exists.
3. Run migrations:

```bash
d:/BTTS/.venv/Scripts/python.exe manage.py migrate
```

4. Create superuser:

```bash
d:/BTTS/.venv/Scripts/python.exe manage.py createsuperuser
```

5. Run server:

```bash
d:/BTTS/.venv/Scripts/python.exe manage.py runserver
```

## API Docs

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI schema: `/api/schema/`

## Main API Groups

### Auth and Users

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`
- `GET /api/auth/users/`
- `GET /api/auth/users/search/`

### Buses and Seats

- Admin bus CRUD: `/api/admin/buses/`
- Seats by bus: `GET /api/buses/<bus_id>/seats/`

Notes:

- Seats are auto-generated from bus capacity.
- Seat IDs are integers.

### Routes

- Admin route CRUD: `/api/admin/routes/`

### Trips

- Admin trip CRUD: `/api/admin/trips/`
- Assign driver: `PATCH /api/admin/trips/<trip_id>/assign-driver/`
- Passenger trip list/search: `/api/passenger/trips/`
- Driver assigned trips: `/api/driver/trips/`
- Driver status update: `PATCH /api/driver/trips/<trip_id>/status/`

### Tickets (Booking)

- Passenger tickets: `/api/passenger/tickets/`
- Book ticket: `POST /api/passenger/tickets/`
- Cancel ticket: `PATCH /api/passenger/tickets/<ticket_id>/cancel/`

Booking request body:

```json
{
  "trip_id": "<trip_uuid>",
  "seat_id": 1
}
```

### Tracking (Step 6)

- Driver location update:
  - `POST /api/tracking/trips/<trip_id>/location/`
- Current trip location:
  - `GET /api/tracking/trips/<trip_id>/current-location/`

Driver location update body:

```json
{
  "latitude": "-1.292100",
  "longitude": "36.821900"
}
```

Notes:

- Driver location is client-driven (frontend/mobile sends periodic GPS updates).
- Backend stores every point and returns latest point as current location.

## IDs

- UUID IDs: users, buses, routes, trips, tickets, payments, locations
- Integer IDs: seats

## Testing

Run full suite:

```bash
d:/BTTS/.venv/Scripts/python.exe manage.py test -v 1
```

Run checks:

```bash
d:/BTTS/.venv/Scripts/python.exe manage.py check
```
