# RP Marketplace Database

This folder contains local MySQL database setup and migration files for RP Marketplace.

## Current Status

Notifications, Reports, Users, Authentication, login logs, and Products use MySQL when their feature flags are enabled. Purchase Requests, Wishlists, Messages, and all other JSON files still use the existing JSON storage.

Do not update Docker, Docker Compose, Jenkins, Ansible, staging, production, or deployment configuration for database work yet.

## Required Environment Variables

Create a local `.env` file at the project root using `.env.example` as the template:

```env
USE_MYSQL_NOTIFICATIONS=true
USE_MYSQL_REPORTS=true
USE_MYSQL_USERS=true
USE_MYSQL_LOGIN_LOGS=true
USE_MYSQL_PRODUCTS=true
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=rp_marketplace
```

Put your real local MySQL password only in `.env`. Do not commit `.env`.

## Create The Database And Table

Using MySQL Workbench:

1. Open a local MySQL connection.
2. Open `database/schema.sql`.
3. Run the full script.

`schema.sql` creates the `rp_marketplace` database and the current migrated tables only.

You can also run `database/notifications.sql` when you only want the notifications table setup and verification queries.

Run `database/reports.sql` when you only want the reports table setup and verification queries.

Run `database/users.sql` and `database/login_attempts.sql` for user/authentication table setup and verification.

Run `database/products.sql` for categories/products setup and verification.

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

The product migration reports seller values that cannot be matched to a user. It preserves those seller strings in `seller_identifier` and does not create fake users.

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
```

Switch back to the JSON fallback:

```env
USE_MYSQL_NOTIFICATIONS=false
USE_MYSQL_REPORTS=false
USE_MYSQL_USERS=false
USE_MYSQL_LOGIN_LOGS=false
USE_MYSQL_PRODUCTS=false
```

When JSON fallback is enabled, the app continues to use `backend/data/notifications.json`.

## Future Migration Order

1. Reports
2. Users and Authentication
3. Products
4. Purchase Requests
5. Wishlists
6. Messages
7. Remove JSON runtime storage
8. Update Docker/Jenkins/Ansible only after local MySQL is complete
