# RP Marketplace Database

This folder contains the local MySQL schema, setup command, module SQL files, and migration scripts for RP Marketplace.

## Current Status

MySQL is the only runtime data store. Normal application routes and services must read and write through `backend/db.py` and the MySQL schema. JSON files are archived seed data only.

Docker containers must connect to the existing host MySQL Server with the same
runtime MySQL settings. When MySQL runs on the Windows host, use
`MYSQL_HOST=host.docker.internal` for Docker.

## Environment

Create a local `.env` from `.env.example`:

```env
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=
SESSION_SECRET=

# Migration-only fallback owner for legacy product seed data.
LEGACY_PRODUCT_OWNER_USERNAME=
```

Put real credentials only in `.env`. Do not commit `.env`.

`LEGACY_PRODUCT_OWNER_USERNAME` is used only by the legacy product migration when archived seed data contains sellers that cannot be matched to users. It is not required for normal Flask startup.

## Teammate Setup

```powershell
git checkout main
git pull origin main
copy .env.example .env
# Fill in local MySQL credentials.
# Start local MySQL Server.
python database/init_database.py
python database/init_database.py --verify
python app.py
```

## Official Setup Command

`database/schema.sql` is authoritative. Run the initializer to create the schema and import archived seed data:

```powershell
python database/init_database.py
```

Run read-only verification:

```powershell
python database/init_database.py --verify
```

The verification command checks required tables, required columns, and row counts. Initialization is designed to be safe to run more than once without duplicating migrated data.

## Archived JSON Seed Data

Legacy JSON files live in:

```text
database/legacy_seed_data/
```

They are retained for migration input, backup, and reference only. Do not edit archived JSON files for new application data. New runtime data belongs in MySQL.

The legacy failed-login source may contain malformed or historically inconsistent data. Migration scripts report JSON decode or shape problems instead of silently repairing legacy corruption.

## Migration Order

`python database/init_database.py` runs migrations in this order:

1. Notifications
2. Reports
3. Users
4. Login Attempts
5. Products
6. Purchase Requests
7. Wishlists
8. Messages

Individual migration scripts still support `--dry-run` when you need to inspect archived seed data import behavior.

## Database Changes

New features requiring database changes must update:

- `database/schema.sql`
- A module SQL file if appropriate
- Migration/setup logic
- Service-layer MySQL queries
- Tests
