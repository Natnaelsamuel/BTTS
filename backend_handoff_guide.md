# Zemen Bus — Backend Handoff Guide

> This document provides a comprehensive overview of the Zemen Bus backend for incoming team members. It covers the architecture, key files, API patterns, authentication, database, development setup, testing, deployment, and common troubleshooting.

---

## 1. Overview

### 1.1 Purpose

The backend is a **Django REST API** that powers the Zemen Bus application. It handles:

- **User management** — registration, login, roles (passenger, driver, admin)
- **Trips** — scheduling and managing bus trips
- **Routes** — defining origin/destination routes
- **Tickets** — booking, payment processing, and PDF ticket generation
- **Notifications** — alerts and communication with users
- **Analytics** — reporting and data aggregation

### 1.2 Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12 (recommended) |
| **Framework** | Django 6, Django REST Framework (DRF) |
| **Database** | PostgreSQL |
| **Authentication** | SimpleJWT (JSON Web Tokens) |
| **API Documentation** | drf-spectacular (OpenAPI / Swagger) |
| **Task Processing** | Synchronous (Celery is **not** used) |
| **Email** | Django's built-in mail backend |

### 1.3 High-Level Request Flow

```
Client Request
     │
     ▼
REST Endpoint (urls.py)
     │
     ▼
View / ViewSet (views.py)
     │
     ▼
Serializer — validates input, shapes output (serializers.py)
     │
     ▼
Service / Helper — business logic, PDF generation, payment calls
     │
     ▼
Model (models.py) — ORM interaction with PostgreSQL
     │
     ▼
Response returned to client
     │
     ├── (optional) Email sent via Django mail backend
     └── (optional) PDF ticket file generated
```

---

## 2. Architecture

### 2.1 Project Layout

The backend is a **monolithic Django project** at the repository root, organized into **one app per domain**:

```
project_root/
├── manage.py                  # Project entry point
├── settings.py                # Django settings (DB, auth, middleware, etc.)
├── urls.py                    # Root URL dispatcher
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (DO NOT commit)
├── .env.example               # Template for .env
├── schema.yaml                # OpenAPI spec (auto-generated)
├── README.md                  # Project overview
├── SETUP.md                   # Setup instructions
│
├── users/                     # User management app
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── password_validation.py
│   ├── tests.py
│   └── migrations/
│
├── tickets/                   # Ticket booking & payments
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── ticket_pdf.py
│   ├── payment_service.py
│   ├── tests.py
│   └── migrations/
│
├── trips/                     # Trip scheduling
├── routes/                    # Route definitions
├── buses/                     # Bus fleet management
├── notifications/             # User notifications
├── feedback/                  # User feedback
└── ...
```

### 2.2 Layering

```
┌─────────────────────────────────────────────┐
│              Views (DRF)                    │  ← HTTP handling
├─────────────────────────────────────────────┤
│            Serializers                      │  ← Validation & representation
├─────────────────────────────────────────────┤
│         Services / Utilities                │  ← Business rules, PDF, payments
├─────────────────────────────────────────────┤
│              Models (ORM)                   │  ← Database persistence
└─────────────────────────────────────────────┘
```

**Rule of thumb**: Views should stay thin. Business logic belongs in **service modules** (e.g., `payment_service.py`, `ticket_pdf.py`, `analytics_service.py`), not in views or serializers.

---

## 3. Key Files Reference

| File | Purpose |
|---|---|
| `manage.py` | Entry point — run dev server, migrations, tests |
| `settings.py` | All Django configuration (DB, JWT, email, pagination, CORS) |
| `urls.py` | Root URL routing — dispatches to each app's URLs |
| `schema.yaml` | Auto-generated OpenAPI specification (via drf-spectacular) |
| `requirements.txt` | All Python dependencies |
| `SETUP.md` / `README.md` | Setup instructions and project overview |
| `.env.example` | Template for environment variables |
| `users/models.py` | User model (custom user with roles) |
| `users/password_validation.py` | `StrongPasswordValidator` — central password policy |
| `tickets/ticket_pdf.py` | PDF ticket generation logic |
| `tickets/payment_service.py` | Payment gateway integration (Chapa or similar) |
| `*/tests.py` | Unit and API tests for each app |

---

## 4. API & Endpoints

### 4.1 Endpoint Pattern

All endpoints follow REST conventions using DRF **ViewSets** and **APIViews**, grouped by app:

| Prefix | App | Examples |
|---|---|---|
| `/api/users/` | Users | Register, login, profile, change password |
| `/api/tickets/` | Tickets | Create ticket, list tickets, payment webhook |
| `/api/trips/` | Trips | List trips, create trip, trip details |
| `/api/routes/` | Routes | List routes, create route |
| `/api/buses/` | Buses | Fleet management |
| `/api/notifications/` | Notifications | User alerts |
| `/api/feedback/` | Feedback | User feedback submission |

### 4.2 Typical Request Flow (Example: Create Ticket)

```
POST /api/tickets/
     │
     ▼
TicketView.perform_create()
     │
     ▼
TicketSerializer.validate()     ← checks trip availability, seat count, user
     │
     ▼
Ticket.objects.create()         ← saves to DB
     │
     ▼
payment_service.initiate()      ← calls payment gateway
     │
     ▼
ticket_pdf.generate()           ← generates PDF ticket
     │
     ▼
Response: 201 Created + ticket data
```

### 4.3 Pagination & Filtering

- Standard DRF pagination is enabled globally in `settings.py`
- List endpoints return paginated results by default
- Filtering is configured per-view using DRF filter backends

### 4.4 Key Endpoints to Know

| Action | Method | Endpoint |
|---|---|---|
| Register | POST | `/api/users/register/` |
| Login (get tokens) | POST | `/api/users/login/` |
| Refresh token | POST | `/api/users/token/refresh/` |
| Change password | POST | `/api/users/change-password/` |
| Create ticket | POST | `/api/tickets/` |
| Payment webhook | POST | `/api/tickets/payment-webhook/` |
| Admin: create driver | POST | `/api/users/create-driver/` |
| List trips | GET | `/api/trips/` |
| API docs (Swagger) | GET | `/api/schema/swagger/` |
| API schema (YAML) | GET | `/api/schema/` |

---

## 5. Authentication & Authorization

### 5.1 Auth Mechanism

| Context | Method |
|---|---|
| **API access** | JWT via **SimpleJWT** — access token + refresh token |
| **Django Admin** | Session-based authentication |

- Access tokens are sent in the `Authorization: Bearer <token>` header
- Token lifetimes and refresh behavior are configured in `settings.py` under `SIMPLE_JWT`

### 5.2 Permissions & Roles

| Role | Description | How it's checked |
|---|---|---|
| **Passenger** | Regular user — books tickets, views trips | Default role on registration |
| **Driver** | Assigned by admin — manages assigned trips | `is_driver` field on User model |
| **Admin** | Full access — manages users, routes, buses, analytics | `is_staff` field on User model |

- **DRF permission classes** are applied on each view to enforce role-based access
- Additional role checks happen inside serializers and views (e.g., only admins can create drivers)

### 5.3 Password Policy

- Enforced by `users.password_validation.StrongPasswordValidator`
- Also validated in serializers via `validate_password()`
- All apps that create or update passwords must go through this validator

### 5.4 Email Flows

| Flow | Trigger | Notes |
|---|---|---|
| **Password reset** | User requests reset | Sends email with reset link/token |
| **Driver onboarding** | Admin creates driver account | Sends welcome email with temporary credentials |

> **Dev vs. Prod**: In local development, `EMAIL_BACKEND` is set to `console` (emails print to terminal). In production, it must be set to an SMTP backend with valid credentials.

---

## 6. Data & Database

### 6.1 Database

| Environment | Database |
|---|---|
| **Production** | PostgreSQL |
| **Local Dev** | PostgreSQL (configured in `settings.py` / `.env`) |

### 6.2 Key Models & Relationships

```
User
 │
 ├── 1:N ──► Ticket (a user books many tickets)
 │
Ticket
 │
 ├── N:1 ──► Trip (many tickets belong to one trip)
 │
Trip
 │
 ├── N:1 ──► Route (many trips run on one route)
 │
Route
 │
 ├── References ──► origin, destination
 │
Payment
 │
 └── 1:1 ──► Ticket (one payment per ticket)
```

### 6.3 Migrations Workflow

```bash
# After making changes to any models.py:
python manage.py makemigrations

# Apply migrations to the database:
python manage.py migrate
```

- Each app has its own `migrations/` directory
- **Never edit migration files manually** unless resolving a conflict
- Use `--keepdb` flag during tests to avoid the interactive "delete test DB?" prompt:
  ```bash
  python manage.py test --keepdb
  ```

---

## 7. Local Development Setup

### 7.1 Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.12** | Recommended on Windows — `psycopg2` wheels available without MSVC |
| **PostgreSQL** | Must be installed and running locally |
| **Git** | For cloning the repository |

### 7.2 Setup Steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd <project-directory>

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env         # Windows
cp .env.example .env           # Linux/Mac
# Then edit .env with your local values

# 5. Run database migrations
python manage.py migrate

# 6. Create a superuser (admin account)
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver
```

### 7.3 Environment Variables (`.env`)

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key | `django-insecure-change-this-in-prod` |
| `DEBUG` | Debug mode (True for dev, False for prod) | `True` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@localhost:5432/zemen_db` |
| `EMAIL_BACKEND` | Email backend class | `django.core.mail.backends.console.EmailBackend` |
| `EMAIL_HOST` | SMTP host (prod only) | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | `app@example.com` |
| `EMAIL_HOST_PASSWORD` | SMTP password / app password | `your-app-password` |
| `CHAPA_SECRET_KEY` | Payment gateway API key | `CHASECK_TEST-...` |

These are read in `settings.py` — **never hardcode secrets**.

### 7.4 Common Gotcha

> **`psycopg2` build fails on Windows?**
> This happens when your Python version doesn't have pre-built `psycopg2` wheels. **Use Python 3.12** to avoid needing MSVC build tools. Alternatively, install `psycopg2-binary` for development (not recommended for production).

---

## 8. Testing & Quality

### 8.1 Test Layout

- Each app has its own `tests.py` (and sometimes `api_tests.py`)
- Tests cover unit logic, serializer validation, and API endpoint behavior

### 8.2 Running Tests

```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test users
python manage.py test tickets

# Avoid the interactive "delete test DB?" prompt
python manage.py test --keepdb
```

### 8.3 What to Validate During Handoff

Before accepting the handoff, run and verify:

- [ ] `python manage.py test users` — all user tests pass
- [ ] `python manage.py test tickets` — all ticket tests pass
- [ ] Smoke-test the auth flow: register → login → get token → access protected endpoint
- [ ] Smoke-test ticket PDF generation: create a ticket and verify the PDF file is produced

---

## 9. Deployment & Environment

### 9.1 Configuration

- `settings.py` reads all sensitive values from **environment variables**
- In production, secrets must be stored in a **CI secret store** or environment config — never in source code

### 9.2 Database in Production

```bash
# Always run migrations after deploying new code
python manage.py migrate

# Back up the database before major changes
pg_dump -U db_user -h db_host zemen_db > backup_$(date +%Y%m%d).sql
```

### 9.3 Static & Media Files

| Type | Location | Notes |
|---|---|---|
| **Static files** | Collected via `collectstatic` | CSS, JS for Django Admin |
| **Generated PDFs** | Written by `ticket_pdf.py` | Ticket files served to users |
| **Media/uploads** | `MEDIA_ROOT` setting | Any user-uploaded content |

### 9.4 External Services

| Service | Purpose | Required Config |
|---|---|---|
| **Chapa** (or similar) | Payment processing | `CHAPA_SECRET_KEY` in `.env` |
| **SMTP Provider** | Sending emails (reset, onboarding) | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` |

---

## 10. Common Tasks

### Add a New Endpoint

1. Define or update the **model** in `models.py` (if new data is needed)
2. Run `python manage.py makemigrations` + `migrate`
3. Create or update the **serializer** in `serializers.py`
4. Create or update the **view** in `views.py`
5. Register the URL in the app's `urls.py`
6. Write **tests** in `tests.py`
7. Regenerate the API schema: `python manage.py spectacular --file schema.yaml`

### Add a Database Migration

1. Modify the model in `models.py`
2. Run:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Commit the new migration file in `migrations/`

### Change Email Templates

- Email subjects and body content are typically defined in `views.py` (for driver onboarding, password reset, etc.)
- Modify the relevant view or create a template file if using Django's template engine

### Fix Failing Tests

1. Run the specific app's tests to isolate the failure:
   ```bash
   python manage.py test <app_name> --verbosity=2
   ```
2. Read the traceback carefully
3. Common causes: serializer validation changes, password policy updates, model field changes

---

## 11. Troubleshooting Checklist

| Problem | Solution |
|---|---|
| **`Failed to install psycopg2`** | Install MSVC build tools, or switch to **Python 3.12** which has pre-built wheels |
| **Driver creation failing** | The temporary password generator may not meet the password policy. Either provide a compliant password or update the generator in the onboarding logic |
| **Interactive DB prompt during tests** | Use `python manage.py test --keepdb`, or manually delete the test database |
| **Auth token not working** | Check `SIMPLE_JWT` settings in `settings.py`. Verify the frontend is storing and sending the token with the correct key. Test the `/api/users/token/refresh/` endpoint |
| **Emails not sending in dev** | Check `EMAIL_BACKEND` in `.env`. For local dev it should be `django.core.mail.backends.console.EmailBackend` (prints to terminal). For prod, set real SMTP credentials |
| **Migration conflicts** | Run `python manage.py makemigrations --merge` to auto-resolve, or manually edit the conflicting migration files |
| **`ModuleNotFoundError`** | Make sure the virtual environment is activated and `pip install -r requirements.txt` was run |

---

## 12. Documentation & Handoff Materials

### Essential Files to Share

| File | What it contains |
|---|---|
| `README.md` | Project overview and introduction |
| `SETUP.md` | Step-by-step local setup instructions |
| `.env.example` | Template for all required environment variables |
| `schema.yaml` | Complete OpenAPI specification for all endpoints |
| `requirements.txt` | All Python dependencies with versions |

### Quick Command Reference

```bash
# Setup
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt

# Migrations
python manage.py makemigrations && python manage.py migrate

# Run server
python manage.py runserver

# Run tests
python manage.py test --keepdb

# Create admin
python manage.py createsuperuser

# Generate API schema
python manage.py spectacular --file schema.yaml
```

### Where to Find Business Logic

| File | What it handles |
|---|---|
| `tickets/payment_service.py` | Payment gateway integration |
| `tickets/ticket_pdf.py` | PDF ticket generation |
| `tickets/ticket_lifecycle.py` | Ticket state management |
| `*/analytics_service.py` | Reporting and data aggregation |
| `users/password_validation.py` | Password strength enforcement |

### API Documentation

- **Swagger UI**: Visit `/api/schema/swagger/` when the server is running locally
- **Schema file**: `schema.yaml` at the project root

---

## 13. Contacts & Expectations

### Maintainers

| Name | Role | Email |
|---|---|---|
| _[Add name]_ | Backend Lead | _[Add email]_ |
| _[Add name]_ | Backend Developer | _[Add email]_ |

### Best Practices

- **Always add tests** for new features or bug fixes
- **Regenerate `schema.yaml`** after any endpoint changes
- **Document DB and ENV changes** in `SETUP.md`
- **Never commit `.env`** — only `.env.example`
- **Run the full test suite** before pushing changes
