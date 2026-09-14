# Spec Kit Azure Interview

[![CI](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/ci.yml/badge.svg)](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/ci.yml)
[![CodeQL](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/codeql.yml/badge.svg)](https://github.com/RobertAgterhuis/speckit-azure-interview/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A provider-independent GitHub Spec Kit extension that conducts a structured Azure architecture interview before specification-driven infrastructure development begins.

It captures business requirements, Azure landing-zone context, networking, private DNS, existing resources, identity, security, governance, operational requirements, constraints, assumptions, and unresolved decisions.

> New user? Follow the [Quick Start](QUICK-START.md) for prerequisites,
> installation, and the complete command order.

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

## Azure Inventory Discovery

Version 0.4.0 adds optional, subscription-scoped Azure inventory discovery for
brownfield, migration, and extension scenarios. It uses Azure Resource Graph to
collect a minimal resource metadata allowlist before or during the architecture
interview.

The canonical extension command is:

```text
speckit.azure-interview.inventory
```

Collection requires explicit approval, one subscription UUID, and the
`--approve-read-only` safety flag. The generated
`.specify/discovery/azure-inventory.json` artifact remains `unconfirmed` until
the user validates its scope and architectural interpretation.

Discovered resources are not automatically approved for reuse or modification
and are never merged automatically into the confirmed interview context.

See [Azure Inventory Discovery](docs/AZURE-INVENTORY.md) for permissions,
operation, safeguards, reconciliation, and troubleshooting.

## Supported Integrations

The extension remains independent of a specific AI provider.

| Integration | Support level |
|---|---|
| Claude Code | Behaviorally tested |
| OpenAI Codex CLI | Behaviorally tested |
| Hermes Agent with Ollama | Behaviorally tested |
| GitHub Copilot | Preview: structurally verified; behavioral testing requested |
| Other Spec Kit integrations | Expected compatibility; not verified |

Actual behavior depends on the selected model, integration, context window, and
its ability to follow the interview instructions.

GitHub Copilot preview support confirms that Spec Kit initializes the
integration and generates the complete Azure interview skill under
`.github/skills`. It does not yet claim that Copilot follows every behavioral
and safety requirement during a complete interview.

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

Install the immutable release archive:

```powershell
specify extension add azure-interview `
    --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.5.0.zip
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

## Codex CLI Usage

Initialize Spec Kit for Codex from the consuming project:

```powershell
specify init --here --integration codex --script ps
```

The current Spec Kit Codex integration generates project-local skills under:

```text
.agents/skills/
```

Verify the Azure interview skill:

```powershell
Test-Path `
    .\.agents\skills\speckit-azure-interview-run\SKILL.md
```

Expected result:

```text
True
```

Start Codex from the consuming project root:

```powershell
codex
```

Establish the project constitution once:

```text
$speckit-constitution

Define the governing principles for an AVM-based Azure IaC solution.
```

Then start the Azure architecture interview:

```text
$speckit-azure-interview-run

We need an AVM-based Bicep solution for a production workload that must integrate with an existing Azure landing zone. Start a new Azure architecture interview.
```

Codex should explicitly acknowledge that it is using:

```text
speckit-azure-interview-run
```

During the initial interview, Codex should create or update only:

```text
.specify/discovery/azure-context.md
```

It must not create:

```text
.specify/discovery/azure-context.json
```

until all required values are confirmed and the readiness gate can pass.

Codex may request approval when its sandbox cannot access the project files.
Review the exact command and target paths before approving it. Prefer one-time
approval during initial testing.

The interview must not:

- Access Azure without explicit approval.
- Retrieve secrets.
- Generate Bicep or Terraform.
- Run a deployment.
- Run an Azure What-If operation.
- Invent resource identifiers.
- Ask multiple independent questions in one response.
- Mark an incomplete interview as ready for specification.

After the interview is complete, validate the generated JSON:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\validate_context.py `
    .\.specify\discovery\azure-context.json `
    --schema .\.specify\extensions\azure-interview\templates\azure-context.schema.json
```

After successful validation, continue with the Codex form of the core Spec Kit
skills:

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

See [Codex Integration](docs/CODEX.md) for complete setup, expected behavior,
approval guidance, validation, and troubleshooting.

## GitHub Copilot Preview

GitHub Copilot is available as a structurally verified preview integration.

Initialize the consuming project:

```powershell
specify init --here --integration copilot --script ps
```

Install the released extension:

```powershell
specify extension add azure-interview `
    --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.5.0.zip
```

Spec Kit generates the project-local skill at:

```text
.github/skills/speckit-azure-interview-run/SKILL.md
```

Verify:

```powershell
Test-Path `
    .\.github\skills\speckit-azure-interview-run\SKILL.md
```

Expected:

```text
True
```

GitHub Copilot agent skills can be selected based on the prompt and skill
description. To request this skill explicitly, use:

```text
Use the /speckit-azure-interview-run skill.

We need an AVM-based Bicep solution for a production workload that must integrate with an existing Azure landing zone. Start a new Azure architecture interview.
```

The structural integration has been verified without paid Copilot usage. The
complete adaptive interview behavior has not yet been tested by the project
maintainer.

Community testing is requested for:

- Skill activation
- Business-purpose-first behavior
- One primary question per response
- Markdown artifact maintenance
- Deferred JSON generation
- Readiness validation
- Azure safety boundaries
- Specification handoff

See [GitHub Copilot Integration](docs/COPILOT.md) for the support status,
installation, acceptance criteria, and feedback instructions.

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
│   ├── CODEX.md
│   ├── COPILOT.md
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

- [Quick Start](QUICK-START.md)
- [Architecture](docs/ARCHITECTURE.md)
- [GitHub Copilot Integration](docs/COPILOT.md)
- [Codex Integration](docs/CODEX.md)
- [Testing Guide](docs/TESTING.md)
- [Hermes Integration](docs/HERMES.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Status

The project is under active development.

Version `0.3.0` provides:
- Establishes the initial interview workflow, output templates, JSON Schema, validation utility, package tests, CI checks, and Hermes compatibility support.
- Tested Claude Code, OpenAI Codex CLI, and Hermes Agent support.
- GitHub Copilot preview support with structurally verified skill generation
  and an explicit request for community behavioral testing.

## Contributing

Contributions and issue reports are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## License

Licensed under the [MIT License](LICENSE).

## Azure Intended Design

After completing and confirming the Azure architecture interview, generate a
reviewable intended-state design with:

    /speckit.azure-interview.design

The command creates:

- `.specify/design/azure-design-model.json`;
- `.specify/design/azure-design-overview.md` with Mermaid;
- `.specify/design/azure-design-overview.svg`;
- `.specify/design/azure-design-overview.drawio`.

A newly generated design has `designStatus: intended` and
`reviewStatus: unreviewed`. It represents proposed architecture derived from
confirmed interview information; it does not prove deployed Azure state.

Review planned and existing resources, ownership boundaries, network paths,
private endpoints, diagnostic settings, and dependencies before implementation.

See [Azure Intended Design](docs/AZURE-DESIGN.md) for prerequisites, artifact
contracts, overwrite protection, security boundaries, and the review workflow.
