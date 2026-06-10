# Docker Notes

Docker files are kept at the project root because Docker expects them there by default.

- `Dockerfile` builds the Flask application image.
- `docker-compose.yml` runs the app locally on port 5000.
- `backend/data` is mounted as a volume so JSON data remains editable during development.
