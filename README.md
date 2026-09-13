# Spec Kit Azure Interview

[![CI](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/ci.yml)
[![CodeQL](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/codeql.yml/badge.svg)](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A provider-independent GitHub Spec Kit extension that conducts a structured Azure architecture interview before specification-driven infrastructure development begins.

It captures business requirements, Azure landing-zone context, networking, private DNS, existing resources, identity, security, governance, operational requirements, constraints, assumptions, and unresolved decisions.

## Why This Extension Exists

Spec Kit provides a strong specification-driven development workflow. However, Azure infrastructure solutions often require architectural decisions that cannot safely remain implicit when `/speckit.specify` starts.

Examples include:

- Whether the workload uses a hub-spoke topology.
- Which hub and spoke virtual networks must be used.
- Where private DNS zones reside.
- Whether resources such as Key Vault already exist.
- Which resources may be changed.
- Which subscriptions and resource groups are in scope.
- Whether AVM modules are mandatory or preferred.
- Which security and governance controls apply.
- Which assumptions still require validation.

This extension adds a discovery and readiness stage without modifying or forking Spec Kit Core.

## Design Principles

- Extend Spec Kit through its supported extension mechanism.
- Keep Spec Kit Core untouched and independently upgradeable.
- Support multiple AI integrations.
- Ask exactly one primary question per response.
- Establish the business purpose before discussing architecture.
- Adapt questions to the answers already supplied.
- Never silently invent Azure resource identifiers or requirements.
- Separate confirmed facts, decisions, assumptions, and open questions.
- Reuse existing resources only when their identity and ownership are confirmed.
- Require explicit approval before optional read-only Azure discovery.
- Never deploy or modify Azure resources during the interview.
- Produce deployable infrastructure code only in later Spec Kit stages.
- Block handoff until the interview satisfies the readiness gate.

## Supported Integrations

The extension is designed to remain independent of a specific AI provider.

It has been tested with:

- Claude Code
- Hermes Agent with a local Ollama model

It can also be installed into other Spec Kit integrations that support generated skills or commands, including Codex and GitHub Copilot.

Actual behavior depends on the selected model, integration, context window, and its ability to follow the interview instructions.

## Interview Workflow

The interview covers these areas:

1. Business purpose and workload identity
2. Scope and deployment lifecycle
3. Existing Azure estate
4. Network topology
5. Private connectivity and DNS
6. Existing resources and ownership
7. Identity and access
8. Security controls
9. Governance and compliance
10. Reliability and operations
11. Monitoring and observability
12. Delivery and testing
13. Prohibited changes and dependencies
14. Decisions, assumptions, and open questions
15. Readiness assessment and specification handoff

The workflow is adaptive. Irrelevant questions should be skipped, while contradictions and missing blocking information must be resolved explicitly.

## Output Artifacts

The interview maintains a human-readable draft at:

```text
.specify/discovery/azure-context.md
```

This Markdown file evolves throughout the interview.

The machine-readable artifact is created only when every schema-required value can be confirmed:

```text
.specify/discovery/azure-context.json
```

The JSON artifact must validate successfully before the workload is handed to `/speckit.specify`.

## Installation

### Install Spec Kit

Install or update the GitHub Spec Kit CLI by following the official Spec Kit installation instructions.

Verify the installation:

```powershell
specify --version
specify check
```

### Initialize a Test or Workload Project

Run this from the project that will consume the extension:

```powershell
specify init --here --integration claude --script ps
```

Replace `claude` with another supported integration when required.

### Install the Extension from GitHub

```powershell
specify extension add `
    https://github.com/RobertAgterhuis/speckit-azure-interview.git
```

Verify the installation:

```powershell
specify extension list
specify extension info azure-interview
```

### Install from a Local Clone

For local development:

```powershell
specify extension add `
    G:\PERSONAL\REPOS\speckit-azure-interview
```

Install the extension into a separate test project. Do not install it into its own source repository for integration testing.

## Claude Code Usage

Start Claude Code from the initialized workload project:

```powershell
claude
```

Then invoke:

```text
/speckit-azure-interview-run We need an AVM-based Bicep solution that integrates with an existing Azure landing zone. Start a new Azure architecture interview.
```

The generated skill name is derived from the extension command:

```text
speckit.azure-interview.run
```

## Hermes Agent Usage

Some Hermes installations use a custom `HERMES_HOME` and do not automatically discover skills generated in the default user-profile directory.

Install the compatibility adapter:

```powershell
Set-Location G:\PERSONAL\REPOS\speckit-azure-interview

.\scripts\powershell\Install-HermesSkillAdapter.ps1
```

Start Hermes from the consuming project with the interview skill preloaded:

```powershell
hermes --skills speckit-azure-interview-run
```

Then enter the workload description as ordinary language:

```text
We need an AVM-based Bicep solution that integrates with an existing Azure landing zone. Start a new Azure architecture interview.
```

See [Hermes Integration](docs/HERMES.md) for installation details and troubleshooting.

## Validate the Final Context

Install the runtime dependency:

```powershell
python -m pip install -r requirements-runtime.txt
```

Validate a completed context:

```powershell
python scripts/python/validate_context.py `
    .specify/discovery/azure-context.json
```

When validating from a consuming Spec Kit project, use the installed extension paths:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\validate_context.py `
    .\.specify\discovery\azure-context.json `
    --schema .\.specify\extensions\azure-interview\templates\azure-context.schema.json
```

Exit codes:

| Exit code | Meaning |
|---:|---|
| `0` | Validation succeeded |
| `1` | The interview context is invalid |
| `2` | The validator could not process the context or schema |

## Readiness Gate

The interview is ready for specification only when:

- The business purpose is confirmed.
- Scope and ownership are confirmed.
- Relevant Azure subscriptions and resource groups are identified.
- Network and private DNS decisions are resolved.
- Existing-resource reuse is explicitly recorded.
- Security and governance requirements are known.
- No blocking open questions remain.
- No critical assumptions remain unvalidated.
- No unresolved requirement contradictions remain.
- The JSON artifact exists.
- The JSON artifact passes schema and semantic validation.

When these conditions are not met, the extension must continue the interview or clearly report what blocks handoff.

## Security Boundaries

During the interview, the extension must not:

- Create or modify Azure resources.
- Run deployments or Azure What-If operations.
- Retrieve or expose secrets.
- Assume permission to query Azure.
- Change Spec Kit Core files.
- Generate deployable Bicep or Terraform code.
- Treat guessed resource identifiers as confirmed facts.
- Mark an incomplete interview as ready.

Optional Azure discovery must be read-only and requires explicit user approval.

## Development

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Run all checks:

```powershell
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m yamllint extension.yml .yamllint.yml .github
python -m pytest -q
```

See [Testing Guide](docs/TESTING.md) for integration and smoke-test procedures.

## Project Structure

```text
.
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/
│   ├── dependabot.yml
│   └── PULL_REQUEST_TEMPLATE.md
├── commands/
│   └── azure-interview.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── HERMES.md
│   └── TESTING.md
├── scripts/
│   ├── powershell/
│   │   └── Install-HermesSkillAdapter.ps1
│   └── python/
│       └── validate_context.py
├── templates/
│   ├── azure-context-template.md
│   └── azure-context.schema.json
├── tests/
│   ├── fixtures/
│   │   └── valid-context.json
│   ├── test_extension_package.py
│   └── test_validate_context.py
├── .editorconfig
├── .extensionignore
├── .gitattributes
├── .gitignore
├── .yamllint.yml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── extension.yml
├── LICENSE
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements-runtime.txt
└── SECURITY.md
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Testing Guide](docs/TESTING.md)
- [Hermes Integration](docs/HERMES.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Status

The project is under active development.

Version `0.1.0` establishes the initial interview workflow, output templates, JSON Schema, validation utility, package tests, CI checks, and Hermes compatibility support.

## Contributing

Contributions and issue reports are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## License

Licensed under the [MIT License](LICENSE).