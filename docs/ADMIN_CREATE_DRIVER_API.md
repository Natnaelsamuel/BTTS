# Admin Create Driver API

Endpoint: POST /api/users/admin/create-driver/

Purpose: Allow administrators to create driver accounts centrally. The endpoint creates a user with role `DRIVER`, keeps the account active, and emails a temporary password so the driver can log in and reset it on first sign-in.

Authentication & Authorization

- Requires a valid admin access token in `Authorization: Bearer <token>` header.
- Permission class: `IsAdminRole` (admin-only).

Request (JSON)

- `username` (string, required)
- `email` (string, required)
- `first_name` (string, optional)
- `last_name` (string, optional)
- `password` (string, optional) — if omitted, server generates a temporary password and emails it to the driver.

Notes

- Any provided `role` in the request is ignored and forced to `DRIVER`.
- The created user is kept `is_active=True` and `must_change_password=True` so the driver can log in with the temporary password and is forced into the reset flow.
- Server sends the temporary password directly to the provided email.
- Email sending errors are logged; API still returns `201` with created user data if creation succeeded (email failure does not roll back user creation).

Response

- 201 Created: returns the created user's summary (id, username, email, first_name, last_name, role, is_active).

Example curl (replace base URL and token):

```bash
curl -X POST "https://example.com/api/users/admin/create-driver/" \
  -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"driver123","email":"driver@example.com","first_name":"John","last_name":"Smith"}'
```

Testing

- Use Django test client or `python manage.py test users` to run the `users` app tests.
- To test manually, obtain an admin token via `/api/users/token/` and call the endpoint with that token.

Security Considerations

- Rate-limit this endpoint in production to prevent bulk account creation abuse by compromised admin tokens.
- Log who created the account and when (consider adding an audit trail model or using existing admin logs).

Frontend Integration Notes

- Admin UI should POST to this endpoint and show a success/toast message with created user details.
- Optionally prompt admin to upload driver documents and record verification state in admin tools.
