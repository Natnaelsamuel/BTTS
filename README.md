## BTTS Backend (Step 1)

Backend foundation for the Bus Tracking and Ticketing System using Django, Django REST Framework, JWT auth, and PostgreSQL.

### Project Structure

- `config` - Django project configuration
- `users` - Custom user model and auth URLs
- `buses` - Bus domain app
- `routes` - Route domain app
- `trips` - Trip scheduling app
- `tickets` - Ticket and booking app
- `tracking` - Bus location tracking app

### Implemented in Step 1

- Django project scaffolded
- Domain apps created
- DRF installed and configured
- PostgreSQL configuration via environment variables
- Custom user model with roles: `ADMIN`, `PASSENGER`, `DRIVER`
- JWT token endpoints added under `/api/auth/`

### Setup

1. Create a `.env` file in project root (copy from `.env.example`).
2. Ensure PostgreSQL is running and create database `btts_db` (or change env values).
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

### Auth Endpoints

- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `POST /api/auth/token/verify/`
