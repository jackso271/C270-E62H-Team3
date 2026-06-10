# C270-E62H-Team3 RP Marketplace

This is a Flask-based RP Marketplace application for the C270 DevOps project.
It allows RP students to register, log in, browse marketplace items, request to
buy products, and lets admins manage users and login logs.

The application still uses JSON files for storage so it stays simple and easy
for classmates to inspect during development and marking.

## Folder Structure

```text
project-root/
├── backend/
│   ├── app.py                 # Flask app factory and blueprint registration
│   ├── routes/                # Route handlers grouped by feature
│   ├── services/              # Business logic used by routes
│   ├── utils/                 # Shared helpers such as JSON storage
│   └── data/                  # JSON storage files
├── frontend/
│   ├── templates/             # Jinja HTML templates
│   └── static/                # CSS, images, and future JavaScript files
├── tests/                     # Basic pytest validation
├── devops/
│   ├── docker/                # Docker notes
│   ├── jenkins/               # Jenkins notes
│   └── ansible/               # Future deployment automation notes
├── docs/                      # Extra project documentation
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Jenkinsfile
└── .github/workflows/ci.yml
```

## How To Run Locally

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the application:

```bash
python app.py
```

4. Open the app:

```text
http://127.0.0.1:5000
```

Default admin login:

```text
Login ID: admin
Password: admin123
```

## How To Run With Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:5000
```

The compose file mounts `backend/data` so local JSON data remains available
while the container runs.

## Testing

Run the test suite:

```bash
python -m pytest
```

Current tests cover:

- Application startup
- Main public routes
- Student login
- Admin login
- Invalid login handling

## CI/CD Workflow

The GitHub Actions workflow and Jenkins pipeline both follow the same DevOps
validation flow:

1. Check out the project.
2. Install Python dependencies.
3. Run pytest.
4. Build the Docker image.

This ensures the application validates successfully before deployment work
continues.

## Team Collaboration Workflow

Recommended workflow for teammates:

1. Pull the latest code before starting work.
2. Create a feature branch for each task.
3. Keep route code in `backend/routes`.
4. Keep reusable business logic in `backend/services`.
5. Keep shared helper code in `backend/utils`.
6. Keep HTML in `frontend/templates`.
7. Keep CSS, images, and JavaScript in `frontend/static`.
8. Run `python -m pytest` before pushing.
9. Open a pull request so teammates can review changes.

## Notes For Maintainers

- Existing route URLs were preserved during the refactor.
- Root `app.py` remains as a compatibility launcher.
- Flask is configured to load templates from `frontend/templates` and static
  files from `frontend/static`.
- JSON storage defaults to `backend/data`, but tests can use a temporary data
  folder through the Flask `DATA_DIR` config.

## Admin UX Updates

The admin interface uses clearer Account Management wording and includes:

- Account summary cards for total, new, inactive, and blocked accounts.
- Search and filters by account status and role.
- Clearer failed login reasons for wrong password, account not found, blocked
  account, and password reset requests.
- A recent activity section built from available JSON data.
- A demo-friendly forgot password request that logs a security event only.

The product request review page now includes status badges, request counters,
verification progress, and optional rejection reasons. Marketplace browsing and
the main user dashboard were not redesigned.
