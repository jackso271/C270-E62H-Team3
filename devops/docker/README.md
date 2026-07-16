# Docker Notes

The RP Marketplace runtime database is MySQL. Docker containers must receive
the MySQL environment variables at runtime; do not bake credentials into an
image.

- `Dockerfile` builds the Flask application image.
- `.env` is required for local Docker runs and must not be committed.
- Use `MYSQL_HOST=host.docker.internal` when MySQL Server runs on the Windows host.
- Legacy JSON files are migration archives under `database/legacy_seed_data/`;
  Docker must not mount `backend/data` as runtime storage.
