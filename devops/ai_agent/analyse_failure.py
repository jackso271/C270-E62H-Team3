import argparse
import os
from pathlib import Path

from devops.ai_agent.providers.base_provider import LocalRuleBasedProvider
from devops.ai_agent.providers.openai_provider import OpenAIProvider
from devops.ai_agent.redact_sensitive_data import redact_sensitive_data
from devops.ai_agent.report_generator import generate_report


DEFAULT_MAX_CHARS = 12000


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def relevant_section(text, max_chars=DEFAULT_MAX_CHARS):
    if not text:
        return ""
    markers = ["ERROR", "FAILED", "fatal:", "UNREACHABLE", "Traceback", "Exception", "script returned exit code"]
    lines = text.splitlines()
    first = 0
    for index, line in enumerate(lines):
        if any(marker in line for marker in markers):
            first = max(index - 20, 0)
            break
    section = "\n".join(lines[first:])
    return section[-max_chars:]


def detect_failed_stage(text):
    stage = None
    for line in text.splitlines():
        stripped = line.strip()
        if "Entering stage" in stripped:
            stage = stripped.rsplit("Entering stage", 1)[-1].strip(" :'\"")
        if stripped.startswith("[Pipeline] { (") and stripped.endswith(")"):
            stage = stripped.removeprefix("[Pipeline] { (").removesuffix(")")
        if "script returned exit code" in stripped or "ERROR:" in stripped or "Finished: FAILURE" in stripped:
            return stage
    return stage


def detect_ansible_details(text):
    details = {"failed_task": None, "host": None, "recap": None}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("TASK [") and "]" in stripped:
            details["failed_task"] = stripped.split("TASK [", 1)[1].split("]", 1)[0]
        if stripped.startswith("fatal: ["):
            details["host"] = stripped.split("[", 1)[1].split("]", 1)[0]
        if "failed=" in stripped and "unreachable=" in stripped:
            details["recap"] = stripped
    return details


def provider_from_env():
    enabled = os.getenv("AI_DIAGNOSTICS_ENABLED", "false").lower() == "true"
    provider_name = os.getenv("AI_PROVIDER", "local").lower()
    if enabled and provider_name == "openai":
        return OpenAIProvider(timeout=int(os.getenv("AI_DIAGNOSTICS_TIMEOUT", "10")))
    return LocalRuleBasedProvider()


def analyse(source, input_file, output_file, provider=None):
    max_chars = int(os.getenv("AI_DIAGNOSTICS_MAX_CHARS", str(DEFAULT_MAX_CHARS)))
    raw_text = read_text(input_file)
    sanitized = redact_sensitive_data(relevant_section(raw_text, max_chars=max_chars))

    context = {
        "source": source,
        "sanitized_log": sanitized,
        "failed_stage": detect_failed_stage(raw_text) if source == "jenkins" else None,
    }
    if source == "ansible":
        context.update(detect_ansible_details(raw_text))

    selected_provider = provider or provider_from_env()
    result = selected_provider.analyse(context)
    result["source"] = source
    result.setdefault("failed_stage", context.get("failed_stage"))
    result.setdefault("failed_task", context.get("failed_task"))

    report = redact_sensitive_data(generate_report(result))
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a read-only CI/CD diagnostic report.")
    parser.add_argument("--source", choices=["jenkins", "ansible"], required=True)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args(argv)

    analyse(args.source, args.input_file, args.output_file)
    print(f"Diagnostic report written to {args.output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
