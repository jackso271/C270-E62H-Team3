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

Docker is used to package the Flask application so it can run consistently in a container during local testing, Jenkins builds, and Ansible deployment.

### Docker Prerequisites

- Docker Desktop or Docker Engine installed
- Docker service started
- Project cloned locally
- Terminal opened at the project root folder

Check that Docker is installed:

```bash
docker --version
```

Check that Docker can run commands:

```bash
docker ps
```

### Build Docker Image

From the project root folder, build the Docker image:

```bash
docker build -t rp-marketplace .
```

### Run Docker Container

Run the Flask application container on port `5000`:

```bash
docker run -d -p 5000:5000 --name rpmarketplace rp-marketplace
```

Verify that the container is running:

```bash
docker ps
```

Open the application in a browser:

```text
http://127.0.0.1:5000
```

Default admin login:

```text
Login ID: admin
Password: admin123
```

### Stop And Remove Docker Container

Stop the running container:

```bash
docker stop rpmarketplace
```

Remove the stopped container:

```bash
docker rm rpmarketplace
```

### Docker Compose

Docker Compose can also be used for local development and demo setup.

Start the application with Docker Compose:

```bash
docker compose up --build
```

Stop and remove Docker Compose containers:

```bash
docker compose down
```

The compose file mounts `backend/data` so local JSON data remains available while the container runs.

## Jenkins CI/CD Pipeline

Jenkins is used to automate the Continuous Integration and Continuous Deployment workflow. During the CA2 demo, Jenkins shows how code changes can be checked, tested, packaged with Docker, and deployed using Ansible.

### Jenkins Prerequisites

- Jenkins installed and running
- Git installed on the Jenkins machine
- Docker installed on the Jenkins machine
- Ansible installed on the Jenkins machine or available in the deployment environment
- Jenkins has permission to run Docker commands
- GitHub repository is accessible by Jenkins
- Project contains a `Jenkinsfile`

### Create Jenkins Pipeline Job

1. Open Jenkins in the browser.
2. Select `New Item`.
3. Enter a job name such as `rp-marketplace-pipeline`.
4. Select `Pipeline`.
5. Select `OK`.

### Connect Jenkins To GitHub Repository

In the Pipeline job configuration:

1. Go to the `Pipeline` section.
2. Set `Definition` to `Pipeline script from SCM`.
3. Set `SCM` to `Git`.
4. Enter the GitHub repository URL.
5. Select the branch to build, for example:

```text
*/main
```

6. Set `Script Path` to:

```text
Jenkinsfile
```

7. Save the job.

### Run Jenkins Build

Start the pipeline manually:

```text
Build Now
```

Jenkins will read the `Jenkinsfile` from the GitHub repository and run the CI/CD pipeline.

### Jenkins Pipeline Stages

The pipeline is designed to demonstrate the following DevOps stages:

| Stage | Purpose |
| --- | --- |
| Checkout Source | Pulls the latest project code from GitHub. |
| Install Dependencies | Installs Python packages from `requirements.txt`. |
| Run Pytest | Runs automated tests using `python -m pytest`. |
| Build Docker Image | Builds the application image using the Dockerfile. |
| Deploy using Ansible | Runs the Ansible playbook to deploy the Docker container. |

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

Ansible is used to automate local Docker deployment for the C270 demo. Instead of manually stopping, removing, rebuilding, and running containers, the playbook performs those deployment steps consistently.

### Ansible Prerequisites

- Ansible installed
- Docker installed and running
- Project cloned locally
- Terminal opened at the project root folder
- Inventory file available in the `ansible/` folder
- Deployment playbook available in the `ansible/` folder

Check that Ansible is installed:

```bash
ansible --version
```

Move into the Ansible folder:

```bash
cd ansible
```

Test Ansible connectivity:

```bash
ansible all -i hosts -m ping
```

Run the deployment playbook:

```bash
ansible-playbook -i hosts deploy_docker_playbook.yaml
```

### What The Ansible Playbook Does

The deployment playbook automates:

- Verify Docker installation
- Stop existing container
- Remove old container
- Build Docker image
- Run container
- Verify application availability

After a successful deployment, open the application:

```text
http://127.0.0.1:5000
```

Optional Ansible test playbook:

```bash
ansible-playbook -i hosts test_connection_playbook.yaml
```

## DevOps Workflow

Complete CA2 DevOps workflow:

```text
Developer
  |
  v
Feature Branch
  |
  v
Commit
  |
  v
Push
  |
  v
Pull Request
  |
  v
Code Review
  |
  v
Merge to Main
  |
  v
Jenkins
  |
  v
Pytest
  |
  v
Docker Build
  |
  v
Ansible Deploy
  |
  v
Running App
```

## CI/CD Pipeline Summary

| DevOps Component | Role In This Project |
| --- | --- |
| Git/GitHub | Stores source code and tracks project changes. |
| Branches | Allows teammates to work on features separately. |
| Pull Requests | Supports review before changes are merged. |
| Jenkins | Automates the CI/CD pipeline from the repository. |
| Pytest | Verifies the Flask application with automated tests. |
| Docker | Builds and runs the application in a container. |
| Ansible | Automates Docker deployment steps. |
| Flask App | The deployed RP Marketplace web application. |

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
