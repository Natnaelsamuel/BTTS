Admin Create-Driver Endpoint — README

Overview

- This document explains how to integrate a frontend admin UI with the `admin/create-driver/` API endpoint.

Endpoint

- `POST /api/users/admin/create-driver/`
- Admin-only; accepts `username`, `email`, `first_name`, `last_name`, optional `password`.

Recommended Admin UI flow

1. Admin opens "Create Driver" form in admin panel with fields: `username`, `email`, `first_name`, `last_name`, optional `temporary password`, and an optional `send email` toggle (default true).
2. On submit, POST JSON to the endpoint with admin's access token.
3. On success (201): show success message and display created user summary.
4. After creating, the driver signs in with the temporary password and is redirected to the reset-password page to set a new password.

Frontend implementation notes

- Use existing `auth` context to obtain admin token.
- Use `fetch` or `axios` to POST to `/api/users/admin/create-driver/` with `Authorization: Bearer <token>`.
- On success, call admin user list refresh to show the new driver.
- Handle email send failures by showing a warning: "Account created but setup email failed — please resend the temporary password or instruct the driver manually."

Optional enhancements

- Bulk CSV import: allow admins to upload a CSV and create many drivers in one operation (server-side task+job queue recommended).
- Document upload: integrate a document uploader in the admin flow; store temporary verification artifacts and require admin approval.
- Audit logging: store the `created_by` admin id and timestamp for each driver creation in either a custom audit model or by extending the `User` model with `created_by` and `created_at` fields.

Developer commands

- Run tests for the `users` app:

```bash
source .venv/Scripts/activate
python manage.py test users
```

Contact

- If you need frontend components scaffolded for this UI, request a task and I can add a simple React admin page and API wiring.
