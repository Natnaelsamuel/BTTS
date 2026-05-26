now# Zemen Bus — Local setup manual (handoff)

This guide helps another team run **Zemen Bus** on a Windows, macOS, or Linux laptop the same way you do in development: **Django API + PostgreSQL** in one repo, **Vite + React** in the other.

You need **two folders** (two repositories if you use Git):

| Component | Typical folder | Role |
|-----------|----------------|------|
| Backend | `Zemen Bus` | Django REST API, admin, database |
| Frontend | `ZemenBus-frontend/bus-tracker-ui` | Passenger / driver / admin web UI |

---

## 1. Prerequisites

Install these on every machine:

| Tool | Notes |
|------|--------|
| **Python 3.12+** | Django 6 requires a recent Python. Check with `python --version`. |
| **PostgreSQL 14+** | The app uses PostgreSQL only (not SQLite). Install server + `psql` client. |
| **Node.js 20+** (LTS) | For the frontend. Check with `node --version` and `npm --version`. |
| **Git** | To clone the repositories. |

Optional but useful:

-- **pgAdmin** or another DB GUI to inspect `zemenbus_db`.
- A code editor (**VS Code** / **Cursor**).

---

## 2. PostgreSQL — create the database

1. Start the PostgreSQL service (Windows: Services; macOS/Linux: your package manager).
2. Open a terminal and create a database and user (adjust passwords as you like):

```sql
-- Connect as superuser, e.g. psql -U postgres
CREATE DATABASE zemenbus_db;
CREATE USER zemenbus_user WITH PASSWORD 'your_secure_password';
ALTER DATABASE zemenbus_db OWNER TO zemenbus_user;
GRANT ALL PRIVILEGES ON DATABASE zemenbus_db TO zemenbus_user;
```

For the simplest local setup, you can keep the defaults in `.env` (`postgres` / `postgres` / `zemenbus_db`) if your Postgres `postgres` user already has a password you know.

---

## 3. Backend setup (`Zemen Bus`)

### 3.1 Get the code

```bash
cd ZemenBus
```

### 3.2 Virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Environment file

1. Copy `.env.example` to `.env` in the **Zemen Bus** project root (same folder as `manage.py`).
2. Edit `.env` and set at least:
   - `POSTGRES_*` to match the database you created.
   - `DJANGO_SECRET_KEY` to any long random string for local use.

If `.env` is missing, Django still starts with built-in defaults in `config/settings.py`, but your DB credentials must match.

### 3.4 Migrations and superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

Use the superuser to log into **Django admin** at `http://127.0.0.1:8000/admin/` and to create admin/driver accounts as your workflow requires.

### 3.5 Run the API

```bash
python manage.py runserver 0.0.0.0:8000
```

- API base URL: **`http://127.0.0.1:8000/api/`**
- OpenAPI docs: **`http://127.0.0.1:8000/api/docs/`**

---

## 4. Frontend setup (`ZemenBus-frontend/bus-tracker-ui`)

### 4.1 Install dependencies

```bash
cd ZemenBus-frontend/bus-tracker-ui
npm install
```

### 4.2 Point the UI at the API

The app reads **`VITE_API_BASE_URL`**. If the backend runs on port 8000 with default URLs, you can skip this step (the code defaults to `http://localhost:8000/api`).

To set it explicitly, create **`.env.local`** in `bus-tracker-ui`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

If the API runs on another host or port, change this URL accordingly (must end with `/api` as in your project).

### 4.3 CORS

`config/settings.py` allows:

- `http://localhost:5173` and `http://127.0.0.1:5173` (Vite default)

If you run the frontend on another port, add it to `CORS_ALLOWED_ORIGINS` in the backend `settings.py` (or extend settings via env if you add that later).

### 4.4 Run the web app

```bash
npm run dev
```

Open the URL Vite prints (usually **`http://localhost:5173`**).

---

## 5. Typical “first login” flow

1. **Passengers** self-register from the UI (register page).
2. **Admins** and **drivers** are normally created by an admin (e.g. Django admin or in-app admin tools), not self-registered as drivers.
3. Use **`createsuperuser`** for the first admin account, then log in at `/login` with that user if your app maps admin role correctly, or use Django admin to assign roles depending on your `User` model setup.

(Align this with how your team actually provisions admin/driver users today.)

---

## 6. Payments (Chapa) — optional for local demos

Without keys, payment flows may fail or stay in test mode depending on code paths.

To test real checkout locally, set in backend `.env`:

- `CHAPA_SECRET_KEY` — from Chapa dashboard  
- `CHAPA_WEBHOOK_SECRET` — must match what Chapa sends (see `tickets` webhook code)

For **webhooks**, Chapa must reach your machine (e.g. **ngrok** URL added in Chapa + `FRONTEND_URL` / callback URLs as configured in your project).

For **internal demos**, you can rely on admin tools and skip live Chapa if your team agrees.

---

## 7. Email — local development

Default `EMAIL_BACKEND` is the **console** backend: emails print in the terminal running `runserver`, which is enough for password reset OTPs and driver welcome emails during development.

For real SMTP, switch `EMAIL_BACKEND` and set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, etc. in `.env`.

---

## 8. Verify everything

| Check | Command / action |
|--------|------------------|
| Backend | `python manage.py check` |
| DB | `python manage.py migrate` exits with no errors |
| API | Open `http://127.0.0.1:8000/api/docs/` |
| Frontend | `npm run build` succeeds |
| End-to-end | Register passenger, log in, open trips |

---

## 9. Common problems

| Symptom | What to try |
|---------|-------------|
| `could not connect to server` (Postgres) | Postgres service running? `POSTGRES_HOST` / `PORT` correct? Firewall? |
| `password authentication failed` | `.env` password matches the DB user? |
| Frontend “Network Error” / CORS | Backend running? `VITE_API_BASE_URL` correct? Origin in `CORS_ALLOWED_ORIGINS`? |
| 401 after a while | JWT access token expiry — log in again; refresh flow depends on refresh token still valid. |
| Migrations missing | Pull latest code, then `python manage.py migrate` again. |
| Port 8000 in use | `python manage.py runserver 8001` and set `VITE_API_BASE_URL=http://127.0.0.1:8001/api` |

---

## 10. What to hand off to the other team

Give them:

1. **Git URLs** (or zip) for **Zemen Bus** and **ZemenBus-frontend**.
2. This file **`SETUP.md`** and **`.env.example`** from the backend repo.
3. Your **recommended Python and Node versions** (from `python --version` / `node --version` on your machine).
4. Any **secrets** they should not commit (Chapa keys, production DB passwords) via a secure channel, not in email/chat.

They should **never commit** `.env` or real API keys to Git.

---

## 11. Optional: production-style run

This document is for **local development**. Production would use a proper WSGI/ASGI server (e.g. Gunicorn + Nginx), HTTPS, strong `DJANGO_SECRET_KEY`, `DEBUG=False`, locked-down `ALLOWED_HOSTS`, and managed PostgreSQL.

---

**Questions?** Compare their machine to yours: same Python major, same Node LTS, PostgreSQL running, `.env` matches DB, and frontend `VITE_API_BASE_URL` matches where `runserver` listens.
