# Read-Only AI Diagnostics Agent

This package provides Version 1 of the RP Marketplace CI/CD troubleshooting
assistant. It analyses sanitized Jenkins and Ansible failure logs and writes a
Markdown diagnostic report for human review.

```mermaid
flowchart LR
    Push[Developer Push] --> Jenkins[Jenkins Pipeline]
    Jenkins --> Failure[Pipeline Failure]
    Failure --> Logs[Sanitized Log Collector]
    Logs --> Analyser[Rule-Based or AI Analyser]
    Analyser --> Report[Diagnostic Report]
    Report --> Artifact[Jenkins Artifact]
    Artifact --> Human[Human Review]
```

## Safety Model

- Read-only diagnostics only.
- No remediation commands are executed.
- Logs are treated as untrusted data.
- Secrets are redacted before report creation or optional provider calls.
- External AI is disabled by default.
- The rule-based analyser works offline.

## Jenkins Workflow

On pipeline failure, Jenkins writes stage output under `artifacts/`, invokes the
Python analyser, and archives `artifacts/ai-diagnostics/*.md`.

The analyser failure is advisory only and must not mask the original pipeline
result.

## Ansible Workflow

Ansible output is captured with `tee` while preserving the original exit code.
If deployment fails, the captured log is analysed and archived. The playbook is
not retried automatically.

## Configuration

```text
AI_DIAGNOSTICS_ENABLED=false
AI_PROVIDER=openai
OPENAI_API_KEY=<Jenkins credential>
AI_DIAGNOSTICS_MAX_CHARS=12000
AI_DIAGNOSTICS_TIMEOUT=10
AI_DIAGNOSTICS_OPENAI_MODEL=gpt-4.1-mini
```

When `AI_DIAGNOSTICS_ENABLED` is not `true`, the local rule-based provider is
used. If OpenAI is enabled but unavailable, the analyser falls back to the local
provider.

## Manual Usage

```bash
python -m devops.ai_agent.analyse_failure \
  --source jenkins \
  --input-file artifacts/jenkins_failure.log \
  --output-file artifacts/ai-diagnostics/jenkins_report.md
```

```bash
python -m devops.ai_agent.analyse_failure \
  --source ansible \
  --input-file artifacts/ansible_failure.log \
  --output-file artifacts/ai-diagnostics/ansible_report.md
```

## Report Contents

Reports include failed stage/task, category, likely root cause, evidence,
verification steps, suggested remediation, risk level, and a safety notice.

## Limitations

The analyser is heuristic in offline mode. It reduces Mean Time To Resolution by
summarising likely causes and next checks, but human approval remains required
for all fixes.
