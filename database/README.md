# RP Marketplace Database

This folder contains local MySQL database setup and migration files for RP Marketplace.

## Current Status

Notifications, Reports, Users, Authentication, login logs, Products, Purchase Requests, Wishlists, and Messages use MySQL when their feature flags are enabled. JSON files remain as local backups and optional fallback storage while testing is completed.

Do not update Docker, Docker Compose, Jenkins, Ansible, staging, production, or deployment configuration for database work yet.

## Required Environment Variables

Create a local `.env` file at the project root using `.env.example` as the template:

```env
USE_MYSQL_NOTIFICATIONS=true
USE_MYSQL_REPORTS=true
USE_MYSQL_USERS=true
USE_MYSQL_LOGIN_LOGS=true
USE_MYSQL_PRODUCTS=true
USE_MYSQL_REQUESTS=true
USE_MYSQL_WISHLISTS=true
USE_MYSQL_MESSAGES=true
LEGACY_PRODUCT_OWNER_USERNAME=
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=rp_marketplace
```

Put your real local MySQL password only in `.env`. Do not commit `.env`.

## Quick Start

1. Create `.env`.
2. Start MySQL Server.
3. Run:

```powershell
python database/init_database.py
```

4. Start Flask:

```powershell
python app.py
```

## Create The Database And Table

Using MySQL Workbench:

1. Open a local MySQL connection.
2. Open `database/schema.sql`.
3. Run the full script.

`schema.sql` creates the `rp_marketplace` database and the migrated tables.

You can also run `database/notifications.sql` when you only want the notifications table setup and verification queries.

Run `database/reports.sql` when you only want the reports table setup and verification queries.

Run `database/users.sql` and `database/login_attempts.sql` for user/authentication table setup and verification.

Run `database/products.sql` for categories/products setup and verification.

Run `database/purchase_requests.sql`, `database/wishlists.sql`, and
`database/messages.sql` for the remaining marketplace tables and verification
queries.

## Migrate Existing Notifications

The migration script reads only `backend/data/notifications.json`. It does not modify or delete the JSON file.

Dry run first:

```powershell
python database\migrations\migrate_notifications.py --dry-run
```

Run the migration:

```powershell
python database\migrations\migrate_notifications.py
```

The script maps JSON `time` to MySQL `created_at`, preserves valid JSON IDs, uses parameterized SQL, and skips existing rows so it is safe to run more than once.

Migrate reports with the same dry-run-first approach:

```powershell
python database\migrations\migrate_reports.py --dry-run
python database\migrations\migrate_reports.py
```

Migrate users before login attempts:

```powershell
python database\migrations\migrate_users.py --dry-run
python database\migrations\migrate_users.py
python database\migrations\migrate_login_attempts.py --dry-run
python database\migrations\migrate_login_attempts.py
```

Migrate products after users:

```powershell
python database\migrations\migrate_products.py --dry-run
python database\migrations\migrate_products.py
```

Then migrate dependent marketplace data:

```powershell
python database\migrations\migrate_purchase_requests.py --dry-run
python database\migrations\migrate_purchase_requests.py
python database\migrations\migrate_wishlists.py --dry-run
python database\migrations\migrate_wishlists.py
python database\migrations\migrate_messages.py --dry-run
python database\migrations\migrate_messages.py
```

The product migration reports seller values that cannot be matched to a user. It preserves those original seller strings in `legacy_seller_name` and does not create fake users.

Legacy demo sellers are handled with a controlled fallback. The migration first
tries to match each product seller against existing users by username, email,
student ID, or full name. If a seller cannot be matched, the product is assigned
to the configured non-admin fallback user, and the original seller text is
stored in `products.legacy_seller_name` for display. The migration stops with a
clear list of available non-admin usernames if the configured fallback does not
exist or is an admin. It never creates fake users and never uses an admin
account as the fallback owner.

Set this in the local `.env` before migrating legacy products:

```env
LEGACY_PRODUCT_OWNER_USERNAME=jason
```

Each teammate may select a valid local non-admin account, but the team should
use the same agreed fallback username when consistent ownership is required.

## Verify Records

In MySQL Workbench, run:

```sql
USE rp_marketplace;
DESCRIBE notifications;
SELECT COUNT(*) AS notification_count FROM notifications;
SELECT id, title, status, created_at
FROM notifications
ORDER BY created_at DESC, id DESC
LIMIT 10;
```

## Enable Or Disable MySQL Notifications

Use MySQL for Notifications:

```env
USE_MYSQL_NOTIFICATIONS=true
USE_MYSQL_REPORTS=true
USE_MYSQL_USERS=true
USE_MYSQL_LOGIN_LOGS=true
USE_MYSQL_PRODUCTS=true
USE_MYSQL_REQUESTS=true
USE_MYSQL_WISHLISTS=true
USE_MYSQL_MESSAGES=true
```

Switch back to the JSON fallback:

```env
USE_MYSQL_NOTIFICATIONS=false
USE_MYSQL_REPORTS=false
USE_MYSQL_USERS=false
USE_MYSQL_LOGIN_LOGS=false
USE_MYSQL_PRODUCTS=false
USE_MYSQL_REQUESTS=false
USE_MYSQL_WISHLISTS=false
USE_MYSQL_MESSAGES=false
```

When JSON fallback is enabled, the app continues to use the matching files in
`backend/data`.

## Migration Order

1. Schema
2. Notifications
3. Reports
4. Users and Authentication
5. Login Attempts
6. Products
7. Purchase Requests
8. Wishlists
9. Messages

`python database/init_database.py` runs this full order. `python
database/init_database.py --verify` is read-only and only checks the connection,
required tables, required columns, and row counts.
