# RP Marketplace - Republic Polytechnic Student Marketplace

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black)
![Docker](https://img.shields.io/badge/Docker-Containerization-blue)
![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-red)
![Ansible](https://img.shields.io/badge/Ansible-Automation-darkred)
![GitHub](https://img.shields.io/badge/GitHub-Version%20Control-black)

## Overview

RP Marketplace is a Flask-based marketplace platform for Republic Polytechnic students to buy, sell, and request second-hand items. Students can register, log in, browse listings, request to buy products, manage wishlists, and receive notifications. Sellers can manage product listings, while admins can manage accounts and review login activity.

This project demonstrates DevOps practices including:

- Git and GitHub
- Branching and Pull Requests
- Docker Containerization
- Jenkins Continuous Integration
- Ansible Deployment Automation
- Testing and Verification

The application currently uses JSON files for storage so the data remains simple, transparent, and easy for classmates and assessors to inspect during development and marking.

## Features

### Student Features

- Registration and login
- Browse marketplace listings
- Search and category filtering
- Product details page
- Wishlist management
- Request to buy
- Notifications

### Seller Features

- Seller dashboard
- Add listing
- Edit listing
- Delete listing
- Category support

### Admin Features

- Account management
- Successful login logs
- Failed login logs
- Block accounts
- Delete accounts

## Technologies Used

| Area | Technologies |
| --- | --- |
| Backend | Python, Flask |
| Frontend | HTML, CSS |
| Storage | JSON |
| Version Control | Git, GitHub |
| Containerization | Docker |
| CI/CD | Jenkins |
| Automation | Ansible |
| AI Assistance | GitHub Copilot Codex, ChatGPT |

## System Architecture

```text
Users
  |
  v
RP Marketplace
  |
  v
Frontend + Backend
  |
  v
GitHub Repository
  |
  v
Jenkins Pipeline
  |
  v
Docker Image
  |
  v
Docker Container
  ^
  |
Ansible Deployment
```

## Repository Structure

```text
project-root/
|-- backend/
|-- frontend/
|-- ansible/
|-- Dockerfile
|-- .dockerignore
|-- requirements.txt
|-- app.py
|-- README.md
```

Additional project folders and files include:

```text
project-root/
|-- backend/
|   |-- app.py                 # Flask app factory and blueprint registration
|   |-- routes/                # Route handlers grouped by feature
|   |-- services/              # Business logic used by routes
|   |-- utils/                 # Shared helpers such as JSON storage
|   |-- data/                  # JSON storage files
|-- frontend/
|   |-- templates/             # Jinja HTML templates
|   |-- static/                # CSS, images, and future JavaScript files
|-- tests/                     # Basic pytest validation
|-- devops/
|   |-- docker/                # Docker notes
|   |-- jenkins/               # Jenkins notes
|   |-- ansible/               # Deployment automation notes
|-- docs/                      # Extra project documentation
|-- docker-compose.yml
|-- Jenkinsfile
|-- .github/workflows/ci.yml
```

## Local Setup

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

## Docker Setup

Build the Docker image:

```bash
docker build -t rp-marketplace .
```

Run the container:

```bash
docker run -d -p 5000:5000 --name rpmarketplace rp-marketplace
```

Then open:

```text
http://127.0.0.1:5000
```

Docker Compose can also be used for local development:

```bash
docker compose up --build
```

The compose file mounts `backend/data` so local JSON data remains available while the container runs.

## Jenkins CI Pipeline

Jenkins is used to automate the Continuous Integration and deployment workflow. The pipeline:

1. Clones the repository from GitHub.
2. Builds the project.
3. Performs automated verification.
4. Deploys Docker containers.

Successful pipeline output:

```text
Finished: SUCCESS
```

The GitHub Actions workflow and Jenkins pipeline both follow a similar DevOps validation flow:

1. Check out the project.
2. Install Python dependencies.
3. Run pytest.
4. Build the Docker image.

This ensures the application validates successfully before deployment work continues.

## Ansible Deployment

Ansible is used to automate local Docker deployment for the C270 demo. The deployment playbook automates:

- Verify Docker installation
- Stop existing container
- Remove old container
- Build Docker image
- Run container
- Verify application availability

Run the deployment playbook from the `ansible/` folder:

```bash
ansible-playbook -i hosts deploy_docker_playbook.yaml
```

Optional Ansible test commands:

```bash
ansible all -m ping
ansible-playbook test_connection_playbook.yaml
```

## DevOps Workflow

```text
Developer
  |
  v
Feature Branch
  |
  v
Pull Request
  |
  v
Main Branch
  |
  v
Jenkins Pipeline
  |
  v
Docker Build
  |
  v
Container Deployment
  ^
  |
Ansible Automation
```

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

## Team Contributions

Existing contributor details should be kept here as the team updates the project documentation.

| Contributor | Contributions |
| --- | --- |
| Jason | Login System, UI/UX Improvements, Docker, Jenkins CI/CD, Ansible Deployment |

## AI-Assisted Development

This project utilized AI-assisted development tools such as GitHub Copilot Codex and ChatGPT to improve productivity, debugging, refactoring, Docker configuration, Jenkins pipeline setup, Ansible playbooks, and documentation. All generated code and configurations were reviewed, tested, and integrated by the project team.

## Admin UX Updates

The admin interface uses clearer Account Management wording and includes:

- Account summary cards for total, new, inactive, and blocked accounts.
- Search and filters by account status and role.
- Clearer failed login reasons for wrong password, account not found, blocked account, and password reset requests.
- A recent activity section built from available JSON data.
- A demo-friendly forgot password request that logs a security event only.

The product request review page now includes status badges, request counters, verification progress, and optional rejection reasons. Marketplace browsing and the main user dashboard were not redesigned.

## Notes For Maintainers

- Existing route URLs were preserved during the refactor.
- Root `app.py` remains as a compatibility launcher.
- Flask is configured to load templates from `frontend/templates` and static files from `frontend/static`.
- JSON storage defaults to `backend/data`, but tests can use a temporary data folder through the Flask `DATA_DIR` config.

## Future Enhancements

- Database integration
- Email notifications
- HTTPS support
- Cloud deployment
- Domain name integration
- Mobile responsiveness
- Security improvements
- Analytics dashboard
