# Architecture

The project is split into backend, frontend, tests, DevOps, and documentation folders.

- `backend/routes` contains Flask route handlers.
- `backend/services` contains business logic.
- `backend/utils` contains shared helper code.
- `frontend/templates` contains Jinja HTML templates.
- `frontend/static` contains CSS, images, and future JavaScript files.

## Admin And Request UX Improvements

The admin area now uses clearer wording for account management and security
review tasks. The Account Management page includes summary cards for total
accounts, new accounts in the past 7 days, inactive accounts, and blocked
accounts.

Failed login tracking now records clearer reasons:

- `Wrong password`
- `Account not found`
- `Blocked account`
- `Password reset requested`

The login page includes a show/hide password control and a simple demo-friendly
forgot password request. This logs a security event only; it does not send email
or change passwords.

The product request review page shows request counters, status badges, a simple
verification progress indicator, and optional rejection reasons. Marketplace
product browsing and the main user dashboard remain unchanged.
