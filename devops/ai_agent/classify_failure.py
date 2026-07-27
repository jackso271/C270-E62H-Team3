import re


CATEGORIES = [
    "git",
    "dependency-installation",
    "python",
    "testing",
    "linting",
    "security-scan",
    "docker-build",
    "docker-runtime",
    "database",
    "environment-configuration",
    "network",
    "permissions",
    "ssh",
    "ansible",
    "deployment",
    "health-check",
    "unknown",
]


CATEGORY_PATTERNS = [
    ("security-scan", [r"\btrivy\b", r"\bbandit\b", r"\bsafety\b", r"vulnerabilit"]),
    ("git", [r"fatal:.*not a git", r"could not read from remote repository", r"git .* failed"]),
    (
        "dependency-installation",
        [
            r"pip install",
            r"npm install",
            r"could not find a version",
            r"no matching distribution",
            r"externally-managed-environment",
            r"externally managed environment",
            r"pep\s*668",
        ],
    ),
    ("testing", [r"pytest", r"test[s]? failed", r"assertionerror", r"failed .* passed"]),
    ("linting", [r"flake8", r"pylint", r"eslint", r"black --check", r"ruff"]),
    ("docker-build", [r"docker build", r"failed to solve", r"dockerfile", r"buildkit"]),
    ("docker-runtime", [r"docker run", r"container .* exited", r"docker: error", r"port is already allocated"]),
    ("database", [r"mysql", r"unknown column", r"database", r"sqlalchemy", r"connection refused.*3306"]),
    ("environment-configuration", [r"missing .*\.env", r"environment variable", r"secret[_-]?key", r"credentials? .* missing"]),
    ("network", [r"timed out", r"dns", r"temporary failure", r"connection refused", r"network is unreachable"]),
    ("permissions", [r"permission denied", r"access is denied", r"operation not permitted"]),
    ("ssh", [r"ssh", r"host key verification", r"unreachable.*ssh"]),
    ("health-check", [r"health.?check", r"status_code", r"http 500", r"http 503", r"uri module"]),
    ("ansible", [r"fatal: \[", r"unreachable!", r"failed=\d+", r"ansible"]),
    ("python", [r"traceback", r"modulenotfounderror", r"syntaxerror", r"python"]),
    ("deployment", [r"deploy", r"deployment", r"playbook"]),
]


RISK_BY_CATEGORY = {
    "linting": "Low",
    "testing": "Low",
    "dependency-installation": "Medium",
    "environment-configuration": "Medium",
    "docker-build": "Medium",
    "docker-runtime": "Medium",
    "network": "Medium",
    "health-check": "High",
    "database": "High",
    "permissions": "High",
    "ssh": "High",
    "security-scan": "High",
    "deployment": "High",
    "ansible": "High",
    "git": "Medium",
    "python": "Medium",
    "unknown": "Medium",
}


CRITICAL_PATTERNS = [
    r"drop database",
    r"drop table",
    r"truncate table",
    r"credential.*exposed",
    r"secret.*exposed",
    r"private key",
    r"data loss",
]


def classify_failure(text):
    lowered = text.lower()

    for pattern in CRITICAL_PATTERNS:
        if re.search(pattern, lowered):
            return "security-scan", "Critical"

    for category, patterns in CATEGORY_PATTERNS:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return category, RISK_BY_CATEGORY.get(category, "Medium")

    return "unknown", RISK_BY_CATEGORY["unknown"]
