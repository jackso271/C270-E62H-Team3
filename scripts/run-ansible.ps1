param(
    [string]$Inventory = "ansible/hosts",
    [string]$Playbook = "ansible/deploy_staging_playbook.yaml"
)

$ErrorActionPreference = "Stop"

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptPath "..")
Set-Location $repoRoot

Write-Host "RP Marketplace Ansible runner"
Write-Host "Repository: $repoRoot"

docker version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not available. Start Docker Desktop, then rerun this script."
}

if (-not (Test-Path ".env")) {
    throw "Missing .env. Run 'Copy-Item .env.example .env', fill in your local MySQL values, then rerun this script."
}

Write-Host "Building Ansible runner image..."
docker compose --profile tools build ansible-runner
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Running Ansible syntax check..."
docker compose --profile tools run --rm ansible-runner ansible-playbook -i $Inventory $Playbook --syntax-check
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ansible syntax validation failed. Deployment was not started."
    exit $LASTEXITCODE
}

Write-Host "Syntax check passed. Running staging deployment..."
docker compose --profile tools run --rm ansible-runner ansible-playbook -i $Inventory $Playbook
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ansible deployment failed."
    exit $LASTEXITCODE
}

Write-Host "Staging deployment completed successfully."
