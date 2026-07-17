param(
    [ValidateSet("staging", "production")]
    [string]$Environment = "staging",
    [switch]$ConfirmProduction
)

$ErrorActionPreference = "Stop"

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptPath "..")
Set-Location $repoRoot

Write-Host "RP Marketplace Ansible runner"
Write-Host "Repository: $repoRoot"
Write-Host "Environment: $Environment"

$inventory = "ansible/hosts"
$envFile = ".env.$Environment"
$playbook = if ($Environment -eq "production") {
    "ansible/deploy_docker_playbook.yaml"
} else {
    "ansible/deploy_staging_playbook.yaml"
}

if ($Environment -eq "production" -and -not $ConfirmProduction) {
    throw "Production deployment requires explicit confirmation. Rerun with '-Environment production -ConfirmProduction'."
}

docker version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not available. Start Docker Desktop, then rerun this script."
}

if (-not (Test-Path $envFile)) {
    throw "Missing $envFile. Run 'Copy-Item .env.example $envFile', fill in the values, then rerun this script."
}

$rootEnv = ".env"
$backupEnv = ".env.run-ansible.backup"
$hadRootEnv = Test-Path $rootEnv

if (Test-Path $backupEnv) {
    throw "Temporary backup file $backupEnv already exists. Move or remove it manually before running this script."
}

try {
    if ($hadRootEnv) {
        Move-Item -LiteralPath $rootEnv -Destination $backupEnv
    }

    Copy-Item -LiteralPath $envFile -Destination $rootEnv

    Write-Host "Building Ansible runner image..."
    docker compose --profile tools build ansible-runner
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build the Ansible runner image."
    }

    Write-Host "Running Ansible syntax check..."
    docker compose --profile tools run --rm ansible-runner ansible-playbook -i $inventory $playbook --syntax-check
    if ($LASTEXITCODE -ne 0) {
        throw "Ansible syntax validation failed. Deployment was not started."
    }

    Write-Host "Syntax check passed. Running $Environment deployment..."
    docker compose --profile tools run --rm ansible-runner ansible-playbook -i $inventory $playbook
    if ($LASTEXITCODE -ne 0) {
        throw "Ansible deployment failed."
    }

    Write-Host "$Environment deployment completed successfully."
}
finally {
    if (Test-Path $rootEnv) {
        Remove-Item -LiteralPath $rootEnv -Force
    }

    if ($hadRootEnv -and (Test-Path $backupEnv)) {
        Move-Item -LiteralPath $backupEnv -Destination $rootEnv
    }
}
