# Contributing

Thank you for contributing to Spec Kit Azure Interview.

This project adds Azure-specific discovery before the existing Spec Kit
specification workflow. Contributions must preserve compatibility with Spec Kit
Core and supported AI integrations.

## Development Principles

All contributions must:

- Keep Spec Kit Core unmodified.
- Use the extension namespace `speckit.azure-interview`.
- Preserve the adaptive, business-first interview order.
- Avoid introducing Azure write operations.
- Avoid requesting or storing secrets.
- Keep existing-resource intent separate from modification permission.
- Preserve facts, requirements, constraints, decisions, assumptions, and open
  questions as distinct concepts.
- Keep Markdown and JSON handoff semantics aligned.
- Remain compatible with greenfield and brownfield scenarios.
- Include tests for behavioural or schema changes.

## Prerequisites

- Git
- Python 3.10 or later
- Spec Kit compatible with `extension.yml`
- PowerShell 7 for testing the Hermes adapter
- At least one supported AI integration for smoke testing

## Local Setup

Clone the repository and create a virtual environment:

```powershell
git clone https://github.com/RobertAgterhuis/speckit-azure-interview.git
Set-Location .\speckit-azure-interview

py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```



## Run Tests

```powershell
python -m pytest -v
```

Validate the representative context directly:

```powershell
python .\scripts\python\validate_context.py `
    .\tests\fixtures\valid-context.json
```

## Extension Development Installation

Never initialize Spec Kit inside this extension source repository.

Create a separate test project:

```powershell
New-Item `
    -ItemType Directory `
    -Path ..\speckit-azure-interview-test `
    -Force |
    Out-Null

Set-Location ..\speckit-azure-interview-test

specify init `
    --here `
    --integration claude `
    --script ps

specify extension add `
    --dev ..\speckit-azure-interview
```

## Supported Test Scenarios

Changes affecting interview behaviour should be tested against:

1. A vague greenfield workload
2. A brownfield workload with existing resources
3. An existing hub-and-spoke landing zone
4. Private endpoints with centrally owned Private DNS
5. An existing Key Vault that cannot be modified
6. Conflicting user and repository information
7. A resumed incomplete interview
8. A completed interview ready for specification
9. An incomplete interview that must remain blocked

## Coding Standards

### Python

- Use type hints.
- Use UTF-8 file handling explicitly.
- Keep stable process exit codes.
- Avoid unnecessary dependencies.
- Include tests for validation behaviour.
- Keep functions small and deterministic.

### PowerShell

- Use PowerShell 7-compatible syntax.
- Use approved verbs.
- Use `Set-StrictMode -Version Latest`.
- Set `$ErrorActionPreference = "Stop"` for automation scripts.
- Validate paths before file operations.
- Support idempotent execution.
- Never overwrite differing content without explicit `-Force`.
- Create backups before an approved replacement.
- Do not use broad or unresolved destructive paths.

### Markdown

- Use English.
- Keep headings descriptive.
- Keep tables structurally valid.
- Wrap prose at approximately 100 characters where practical.
- Use fenced code blocks with a language identifier.
- Do not include unsupported or unverifiable claims.

### YAML and JSON

- Use two-space indentation.
- Keep enum values stable.
- Reject unexpected JSON properties unless deliberately introduced.
- Update fixtures and tests when the schema changes.
- Use Semantic Versioning for breaking contract changes.

## Changing the Interview Command

When changing `commands/azure-interview.md`:

1. Identify the behaviour being corrected or added.
2. Add or update an automated safeguard test.
3. Test a new interview.
4. Test resume behaviour.
5. Confirm exactly one primary question is asked.
6. Confirm business purpose remains the first unresolved topic.
7. Confirm no Azure writes or IaC generation occur.
8. Confirm the JSON handoff is not created prematurely.
9. Test at least one strong hosted model.
10. Test at least one supported local model where practical.

## Changing the JSON Schema

A schema change must include:

- The updated JSON Schema
- Updated valid fixtures
- New invalid-case tests
- Migration implications
- Changelog entry
- Semantic-version impact assessment

Breaking changes to required properties or enum values require a major version
increment after version `1.0.0`.

## Pull Requests

Pull requests should:

- Address one coherent change.
- Explain the problem and intended outcome.
- Include relevant tests.
- Pass all CI jobs.
- Avoid unrelated formatting changes.
- Update documentation when behaviour changes.
- State which integrations were smoke-tested.
- State whether the change affects generated artifacts.
- State whether the change is breaking.

## Commit Messages

Use clear imperative commit messages.

Examples:

```text
Add Hermes custom-home compatibility adapter
Enforce business-purpose-first interview flow
Validate readiness counters before handoff
Document brownfield resource ownership
```

## Security Issues

Do not disclose security vulnerabilities in a public issue. Follow the process
in `SECURITY.md`.

## License

By contributing, you agree that your contribution will be licensed under the
MIT License.