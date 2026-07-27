from devops.ai_agent.classify_failure import classify_failure


class BaseAIProvider:
    def analyse(self, context):
        raise NotImplementedError


class LocalRuleBasedProvider(BaseAIProvider):
    """Offline read-only analyser used by default."""

    def analyse(self, context):
        source = context.get("source", "unknown")
        sanitized = context.get("sanitized_log", "")
        category, risk = classify_failure(sanitized)
        evidence = context.get("evidence") or extract_evidence(sanitized)

        return {
            "source": source,
            "failed_stage": context.get("failed_stage"),
            "failed_task": context.get("failed_task"),
            "category": category,
            "risk_level": risk,
            "summary": summary_for(source, context, category),
            "likely_root_cause": likely_root_cause(category, evidence),
            "evidence": evidence[:8],
            "recommended_verification": recommended_verification(category, source),
            "suggested_remediation": suggested_remediation(category),
        }


def extract_evidence(text):
    useful_markers = [
        "ERROR",
        "Error",
        "FAILED",
        "fatal:",
        "UNREACHABLE",
        "Traceback",
        "Exception",
        "Unknown column",
        "permission denied",
        "Missing .env",
        "failed=",
        "rc:",
        "stderr:",
        "msg:",
    ]
    evidence = []
    for line in text.splitlines():
        clean = line.strip()
        if clean and any(marker in clean for marker in useful_markers):
            evidence.append(clean[:500])
    return evidence or [text.strip()[:500]] if text.strip() else []


def summary_for(source, context, category):
    if source == "ansible":
        target = context.get("failed_task") or context.get("host") or "an Ansible task"
        return f"Ansible execution failed around {target}."
    stage = context.get("failed_stage") or "a Jenkins stage"
    return f"Jenkins pipeline failed during {stage} with category {category}."


def likely_root_cause(category, evidence):
    joined = " ".join(evidence).lower()
    if category == "database":
        return "The application or deployment expected database state that is not present or reachable."
    if category == "environment-configuration":
        return "A required environment file, variable, or credential appears to be missing or invalid."
    if category == "docker-build":
        return "Docker image build failed, likely due to Dockerfile, context, dependency, or registry issues."
    if category == "docker-runtime":
        return "Docker container execution failed, likely due to runtime configuration, port, image, or command issues."
    if category == "testing":
        return "Automated tests reported one or more failures."
    if category == "permissions" or "permission denied" in joined:
        return "The pipeline or Ansible task lacked permission for the attempted operation."
    if category == "ssh":
        return "Ansible could not connect to the target over SSH or failed SSH validation."
    if category == "health-check":
        return "The deployed service did not pass its HTTP or container health check."
    if category == "dependency-installation":
        if "externally-managed-environment" in joined or "externally managed environment" in joined or "pep 668" in joined:
            return "Dependency installation failed because Python is running in an externally managed environment instead of a project virtual environment."
        return "Dependency installation failed due to package resolution or network/index access."
    return "The sanitized log does not contain enough known patterns for a precise root-cause classification."


def recommended_verification(category, source):
    common = [
        "Review the archived sanitized diagnostic log.",
        "Confirm the failure is reproducible in the intended environment.",
    ]
    category_steps = {
        "database": ["Verify required tables and columns using non-destructive schema inspection.", "Run any required migration in dry-run mode first."],
        "environment-configuration": ["Confirm the expected Jenkins credential or .env file exists.", "Verify required variable names without printing values."],
        "docker-build": ["Build the image locally or in staging with the same Dockerfile.", "Check Docker build context and dependency availability."],
        "docker-runtime": ["Inspect the target container logs.", "Check container name, image, port binding, and environment file."],
        "testing": ["Run the targeted failing tests locally.", "Inspect the first assertion or traceback."],
        "permissions": ["Check file, Docker socket, or workspace permissions.", "Confirm the Jenkins user has required non-destructive access."],
        "ssh": ["Verify inventory target and SSH key configuration.", "Run Ansible ping against the target if safe."],
        "health-check": ["Check application logs.", "Curl the health URL from the same network context."],
    }
    return common + category_steps.get(category, ["Inspect the failed command and nearest error lines."])


def suggested_remediation(category):
    remediations = {
        "database": "Apply the missing idempotent migration after human review, then redeploy to staging first.",
        "environment-configuration": "Create or correct the missing Jenkins credential or environment value without committing secrets.",
        "docker-build": "Fix the Dockerfile, build context, or dependency source, then rebuild in staging.",
        "docker-runtime": "Correct container runtime configuration and retry only after review.",
        "testing": "Fix the failing test or application code path, then rerun the targeted suite.",
        "permissions": "Grant the minimum required permission or adjust the file/socket ownership after review.",
        "ssh": "Correct inventory, SSH key, or host key configuration.",
        "health-check": "Inspect application startup errors and fix the service issue before promotion.",
        "dependency-installation": "Create and use a project virtual environment, then install dependencies through that virtual environment's Python and pip.",
    }
    return remediations.get(category, "Use the evidence above to prepare a human-reviewed remediation plan.")
