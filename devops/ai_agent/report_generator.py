from datetime import datetime, timezone


SAFETY_NOTICE = (
    "This report is advisory only. No remediation command was executed automatically."
)


def bullet_list(items):
    if not items:
        return "- No specific evidence extracted."
    return "\n".join(f"- {item}" for item in items)


def numbered_list(items):
    if not items:
        return "1. Review the failed Jenkins or Ansible stage output."
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def generate_report(result):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    source = result.get("source", "unknown").title()
    failed_stage = result.get("failed_stage") or "Unknown"
    failed_task = result.get("failed_task") or "Unknown"

    source_specific = (
        f"## Failed Task\n{failed_task}\n"
        if result.get("source") == "ansible"
        else f"## Failed Stage\n{failed_stage}\n"
    )

    return f"""# AI Pipeline Diagnostic Report

## Generated At
{generated_at}

## Summary
{result.get("summary", "A pipeline or deployment failure was detected.")}

## Source
{source}

{source_specific}
## Category
{result.get("category", "unknown")}

## Likely Root Cause
{result.get("likely_root_cause", "The exact root cause could not be determined from the available sanitized log.")}

## Evidence
{bullet_list(result.get("evidence", []))}

## Recommended Verification
{numbered_list(result.get("recommended_verification", []))}

## Suggested Remediation
{result.get("suggested_remediation", "Review the evidence and apply a human-reviewed remediation.")}

## Risk Level
{result.get("risk_level", "Medium")}

## Safety Notice
{SAFETY_NOTICE}
"""
