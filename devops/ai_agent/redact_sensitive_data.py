import re
from pathlib import Path


SECRET_VALUE = "[REDACTED]"
SAFE_REDACTION_FAILURE_MESSAGE = (
    "Sanitized diagnostic log unavailable because redaction failed. Raw log was not archived."
)


SECRET_NAME_PATTERN = (
    r"(password|passwd|pwd|secret|token|api[_-]?key|authorization|credential|"
    r"mysql_password|session_secret|flask_secret_key|totp|2fa|private[_-]?key|"
    r"github_token|webhook_secret)"
)


REDACTION_PATTERNS = [
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(mysql://[^:\s/@]+:)([^@\s]+)(@)"),
    re.compile(r"(?i)(mysql\+pymysql://[^:\s/@]+:)([^@\s]+)(@)"),
    re.compile(r"(?i)(otpauth://totp/[^?\s]+[^\s]*)"),
    re.compile(r"(?is)(-----BEGIN [A-Z ]*PRIVATE KEY-----).*?(-----END [A-Z ]*PRIVATE KEY-----)"),
    re.compile(rf"(?i)\b({SECRET_NAME_PATTERN})\b\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)(OPENAI_API_KEY|GITHUB_TOKEN|SESSION_SECRET|MYSQL_PASSWORD)=([^\s]+)"),
]


def redact_sensitive_data(text):
    if text is None:
        return ""

    redacted = str(text)
    redacted = REDACTION_PATTERNS[0].sub(r"\1" + SECRET_VALUE, redacted)
    redacted = REDACTION_PATTERNS[1].sub(r"\1" + SECRET_VALUE, redacted)
    redacted = REDACTION_PATTERNS[2].sub(r"\1" + SECRET_VALUE + r"\3", redacted)
    redacted = REDACTION_PATTERNS[3].sub(r"\1" + SECRET_VALUE + r"\3", redacted)
    redacted = REDACTION_PATTERNS[4].sub(SECRET_VALUE, redacted)
    redacted = REDACTION_PATTERNS[5].sub(r"\1" + SECRET_VALUE + r"\2", redacted)
    redacted = REDACTION_PATTERNS[6].sub(lambda m: f"{m.group(1)}={SECRET_VALUE}", redacted)
    redacted = REDACTION_PATTERNS[7].sub(lambda m: f"{m.group(1)}={SECRET_VALUE}", redacted)
    return redacted


def safe_redact_sensitive_data(text):
    try:
        return redact_sensitive_data(text)
    except Exception:
        return SAFE_REDACTION_FAILURE_MESSAGE


def write_redacted_file(input_file, output_file):
    raw = Path(input_file).read_text(encoding="utf-8", errors="replace")
    Path(output_file).write_text(safe_redact_sensitive_data(raw), encoding="utf-8")
