# Quick Start

Use Spec Kit Azure Interview to complete structured Azure architecture discovery
before starting specification-driven IaC development.

This extension supplements GitHub Spec Kit. It does not replace or modify Spec
Kit Core.

## Workflow Order

Run the workflow in this order:

1. Initialize GitHub Spec Kit.
2. Install Spec Kit Azure Interview.
3. Establish the project constitution.
4. Optionally collect scoped, read-only Azure inventory evidence.
5. Complete and confirm the Azure architecture interview.
6. Generate and review the intended Azure architecture design.
7. Create the specification.
8. Clarify the specification when required.
9. Create the implementation plan.
10. Generate a quality checklist when required.
11. Generate the tasks.
12. Analyze specification, plan, and task consistency.
13. Implement the approved solution.
14. Run convergence checks until the implementation is complete.

The optional inventory command may run before or during the interview:

```text
speckit.azure-interview.inventory
```

Inventory evidence remains `unconfirmed` until it is reconciled with the user
during the Azure interview.

After the interview is complete and `azure-context.json` is confirmed, generate
the intended design:

```text
speckit.azure-interview.design
```

The generated design remains `intended` and `unreviewed` until explicit human
approval. It must be reviewed before Specify and implementation.

The complete workflow is:

```text
Constitution
    ↓
Azure Inventory Discovery (optional)
    ↓
Azure Interview
    ↓
Intended Design Review
    ↓
Specify
    ↓
Clarify (optional)
    ↓
Plan
    ↓
Checklist (optional)
    ↓
Tasks
    ↓
Analyze (recommended)
    ↓
Implement
    ↓
Converge until complete
```
## Optional Azure Inventory Discovery

For brownfield, migration, or extension work, inventory the approved Azure
subscription before completing estate and existing-resource discovery.

The canonical extension command is:

```text
speckit.azure-interview.inventory
```

The generated invocation syntax depends on the active Spec Kit integration.
The command confirms the exact tenant, subscription, output path, and overwrite
behavior before running the collector.

Direct PowerShell invocation from an initialized consuming project:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\collect_azure_inventory.py `
  --subscription <confirmed-subscription-id> `
  --tenant <confirmed-tenant-id> `
  --approve-read-only
```

Default output:

```text
.specify/discovery/azure-inventory.json
```

The artifact remains `unconfirmed`. Continue the Azure architecture interview
to confirm resource relevance, ownership, lifecycle intent, modification
permission, dependencies, and prohibited changes.

Inventory discovery is optional. Skip it for greenfield work or whenever Azure
access is unavailable or not approved.

## Prerequisites

Install the following tools:

- Windows, Linux, or macOS
- Git
- Python 3.11 or later
- `uv`, the recommended Python tool and package manager
- GitHub Spec Kit
- A supported AI coding agent

Supported agents include Claude Code, Hermes Agent, Codex, GitHub Copilot, and
other integrations exposed by your installed Spec Kit version.

List the integrations available in your Spec Kit installation:

```powershell
specify integration list
```

## 1. Install `uv`

On Windows, install `uv` with WinGet:

```powershell
winget install --id Astral-sh.uv
```

Open a new PowerShell terminal after installation.

Verify:

```powershell
uv --version
```

See the official `uv` installation guide for alternative installation methods:

<https://docs.astral.sh/uv/getting-started/installation/>

## 2. Install Original GitHub Spec Kit

### Recommended Stable Installation

Install the published Spec Kit CLI package:

```powershell
uv tool install specify-cli
```

If it is already installed, upgrade it:

```powershell
uv tool upgrade specify-cli
```

### Install a Specific GitHub Release

To pin Spec Kit to a specific release, replace `vX.Y.Z` with an official release
tag:

```powershell
uv tool install specify-cli `
    --force `
    --from git+https://github.com/github/spec-kit.git@vX.Y.Z
```

Review available releases at:

<https://github.com/github/spec-kit/releases>

### Verify Spec Kit

```powershell
specify --version
specify check
specify self check
```

`specify check` verifies the locally available AI integrations and supporting
tools.

## 3. Prepare the Workload Repository

Create or open the repository where the Azure solution will be developed.

Example:

```powershell
New-Item `
    -ItemType Directory `
    -Path C:\Repos\example-azure-workload |
    Out-Null

Set-Location C:\Repos\example-azure-workload

git init
```

For an existing repository, navigate to its root instead:

```powershell
Set-Location C:\Repos\existing-azure-workload
```

Run all following commands from the workload repository, not from the
`speckit-azure-interview` extension source repository.

## 4. Initialize Spec Kit

Choose the integration that matches your AI agent.

### Claude Code

```powershell
specify init --here --integration claude --script ps
```

### Hermes Agent

```powershell
specify init --here --integration hermes --script ps
```

### Codex

```powershell
specify init --here --integration codex --script ps
```

### GitHub Copilot

```powershell
specify init --here --integration copilot --script ps

### Another Integration

List the supported integration identifiers:

```powershell
specify integration list
```

Then initialize using the required identifier:

```powershell
specify init --here --integration <integration-name> --script ps
```

If the repository is non-empty and Spec Kit requests explicit confirmation,
review the affected files before using `--force`.

## 5. Install Spec Kit Azure Interview

Install the immutable `v0.5.0` release archive:

```powershell
specify extension add azure-interview `
    --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.5.0.zip
```

Spec Kit displays an untrusted-source warning because the extension is not yet
distributed through the official Spec Kit extension catalog.

Confirm with `y` only after verifying that the source is:

```text
https://github.com/RobertAgterhuis/speckit-azure-interview
```

Verify the installation:

```powershell
specify extension list
specify extension info azure-interview
```

Expected extension:

```text
Spec Kit Azure Interview (v0.5.0)
```

Expected command:

```text
speckit.azure-interview.run
```

## 6. Install the Runtime Dependency

The JSON context validator requires `jsonschema`.

Create a project-local virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the extension runtime dependency:

```powershell
python -m pip install `
    -r .\.specify\extensions\azure-interview\requirements-runtime.txt
```

Do not install `requirements-dev.txt` in the workload repository. That file is
only used when developing the extension itself.

## 7. Start the AI Agent

Always start the AI agent from the workload repository root.

### Claude Code

```powershell
claude
```

### Codex

Start Codex from the consuming project root:

```powershell
codex
```

The current Spec Kit Codex integration generates skills under:

```text
.agents/skills/
```

Invoke skills with the `$` prefix, for example:

```text
$speckit-azure-interview-run
```

See [Codex Integration](docs/CODEX.md) for complete instructions.

### GitHub Copilot

Open the consuming repository in a GitHub Copilot surface that supports agent
skills, such as agent mode in Visual Studio Code or GitHub Copilot CLI.

The generated Azure interview skill is located at:

```text
.github/skills/speckit-azure-interview-run/SKILL.md
```

Verify the skill:

```powershell
Test-Path `
    .\.github\skills\speckit-azure-interview-run\SKILL.md
```

Expected:

```text
True
```

Request the skill explicitly:

```text
Use the /speckit-azure-interview-run skill.

We need an AVM-based Bicep solution for a production workload that must integrate with an existing Azure landing zone. Start a new Azure architecture interview.
```

GitHub Copilot support is currently classified as:

```text
Preview — structurally verified; behavioral testing requested
```

The project maintainer has verified skill generation without consuming paid
Copilot usage. Complete interview behavior has not yet been verified.

See [GitHub Copilot Integration](docs/COPILOT.md) for:

- Installation instructions
- Structural acceptance criteria
- Behavioral acceptance criteria
- Known limitations
- Community testing guidance
- Troubleshooting

### Hermes Agent

For a standard Hermes installation:

```powershell
hermes
```

For a custom `HERMES_HOME`, follow:

<https://github.com/RobertAgterhuis/speckit-azure-interview/blob/main/docs/HERMES.md>

### Codex

Start Codex according to your local Codex CLI configuration.

## 8. Establish the Constitution

Run Constitution once when starting a new project. Update it later only when the
project-wide principles change.

For integrations that expose generated skills as slash commands:

```text
/speckit-constitution Define the governing principles for an AVM-based Azure IaC solution. Require secure-by-default design, least privilege, private connectivity where appropriate, reusable modules, automated validation, documented ownership boundaries, and no deployment without review.
```

Depending on the integration, the equivalent canonical command may be displayed
as:

```text
/speckit.constitution
```

Review:

```text
.specify/memory/constitution.md
```

Confirm that it contains the required engineering, security, governance,
testing, IaC, and AVM principles before continuing.

## 9. Run the Azure Architecture Interview

Start the interview before `/speckit.specify`.

### Claude Code or Another Slash-Command Integration

```text
/speckit-azure-interview-run We need an AVM-based Bicep solution that integrates with an existing Azure landing zone. Start a new Azure architecture interview.
```

### Hermes Agent

Preload the skill when required by the Hermes installation:

```powershell
hermes --skills speckit-azure-interview-run
```

Then enter the request as ordinary language:

```text
Use the speckit-azure-interview-run skill. We need an AVM-based Bicep solution that integrates with an existing Azure landing zone. Start a new Azure architecture interview.
```

Answer one interview question at a time.

The interview records:

- Business purpose
- Workload scope and lifecycle
- Existing Azure landing-zone context
- Subscriptions and resource groups
- Hub-spoke or Virtual WAN topology
- Hub and spoke ownership
- Private endpoints and Private DNS
- Existing resources such as Key Vault
- Resource reuse, creation, replacement, or import intent
- Identity and RBAC
- Security and compliance
- Governance and FinOps
- Reliability and operations
- Monitoring and observability
- Delivery and testing
- Prohibited changes
- Dependencies
- Decisions
- Assumptions
- Open questions

## 10. Verify Interview Readiness

During the interview, the extension maintains:

```text
.specify/discovery/azure-context.md
```

The final machine-readable artifact is:

```text
.specify/discovery/azure-context.json
```

The JSON artifact is created only when all schema-required information can be
confirmed.

Validate it:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\validate_context.py `
    .\.specify\discovery\azure-context.json `
    --schema .\.specify\extensions\azure-interview\templates\azure-context.schema.json
```

Expected result:

```text
VALID: <absolute-path-to-azure-context.json>
```

Do not continue to specification when:

- The interview status is not `complete`.
- Blocking questions remain.
- Critical assumptions remain unvalidated.
- Required resource identifiers are missing.
- Requirements conflict.
- Blocking dependencies remain unresolved.
- JSON validation fails.
- `readyForSpecification` is `false`.

## 11. Create the Specification

Run Specify only after the interview passes its readiness gate:

```text
/speckit-specify Use .specify/discovery/azure-context.md and .specify/discovery/azure-context.json as authoritative discovery input. Preserve confirmed requirements, ownership boundaries, existing-resource lifecycle intent, constraints, and prohibited changes. Do not convert assumptions into facts and do not invent missing Azure details.
```

Canonical command form:

```text
/speckit.specify
```

Specify defines what must be built and why. It should not prematurely implement
the solution.

## 12. Clarify the Specification

Run Clarify when the specification still contains ambiguity:

```text
/speckit-clarify
```

Canonical command form:

```text
/speckit.clarify
```

If clarification changes an architectural fact, update the discovery artifacts
and revalidate them before planning.

## 13. Create the Implementation Plan

Run Plan after the specification is accepted:

```text
/speckit-plan Create an AVM-based Bicep implementation plan that follows the constitution and the validated Azure discovery context. Preserve all existing-resource ownership and prohibited-change boundaries.
```

Canonical command form:

```text
/speckit.plan
```

The plan should cover:

- AVM module selection
- Custom module justification when AVM coverage is unavailable
- Deployment scopes
- Module boundaries
- Resource dependencies
- Existing-resource references
- Parameters and outputs
- Security controls
- Diagnostic settings
- Validation strategy
- Deployment sequencing
- Rollback or forward-fix strategy

## 14. Generate a Quality Checklist

This step is optional but recommended for production Azure solutions:

```text
/speckit-checklist Generate an implementation-readiness checklist covering Azure architecture, AVM usage, private connectivity, DNS, identity, security, governance, observability, deployment validation, and prohibited changes.
```

Canonical command form:

```text
/speckit.checklist
```

Resolve checklist failures before implementation.

## 15. Generate Tasks

```text
/speckit-tasks
```

Canonical command form:

```text
/speckit.tasks
```

Review the tasks and confirm that they include:

- IaC implementation
- Tests
- Security validation
- Bicep build and linting
- PSRule for Azure where applicable
- Deployment validation
- Azure What-If before deployment
- Documentation
- Operational handover
- Rollback or forward-fix activities

## 16. Analyze Consistency

Run Analyze before implementation:

```text
/speckit-analyze
```

Canonical command form:

```text
/speckit.analyze
```

Resolve critical or high-severity findings across:

- Constitution
- Azure discovery context
- Specification
- Plan
- Checklist
- Tasks

Do not proceed while material contradictions remain.

## 17. Implement

Run Implement only after the artifacts are consistent and approved:

```text
/speckit-implement
```

Canonical command form:

```text
/speckit.implement
```

Review every generated change. Do not authorize an Azure deployment merely
because implementation files were generated successfully.

Before deployment, run the required controls, including:

- Bicep build
- Bicep lint
- Unit or template tests
- PSRule for Azure where applicable
- Azure deployment validation
- Azure What-If
- Security review
- Cost review
- Required approval gates

## 18. Converge

After implementation, assess the repository against the specification, plan,
and tasks:

```text
/speckit-converge
```

Repeat Implement and Converge until the result reports that the implementation
has converged.

```text
Implement
    ↓
Converge
    ↓
Remaining work?
    ├── Yes → update tasks → Implement again
    └── No  → final validation and release
```

## Integration Command Notation

The command notation depends on the selected integration:

| Integration mode | Azure Interview | Constitution | Specify |
|---|---|---|---|
| Codex skills | `$speckit-azure-interview-run` | `$speckit-constitution` | `$speckit-specify` |
| Claude skills | `/speckit-azure-interview-run` | `/speckit-constitution` | `/speckit-specify` |
| Canonical command | `/speckit.azure-interview.run` | `/speckit.constitution` | `/speckit.specify` |
| Hermes preload | `hermes --skills speckit-azure-interview-run` | Integration-dependent | Integration-dependent |

Use the form generated by the selected Spec Kit integration. Do not assume that
slash-command notation and skill notation are interchangeable.

## Command Order Summary

| Order | Command | Required | Purpose |
|---:|---|:---:|---|
| 1 | `/speckit-constitution` | Once per project | Establish governing principles |
| 2 | `/speckit-azure-interview-run` | Yes for Azure IaC | Complete Azure architecture discovery |
| 3 | Context validator | Yes | Enforce the readiness gate |
| 4 | `/speckit-specify` | Yes | Define what and why |
| 5 | `/speckit-clarify` | Optional | Resolve specification ambiguity |
| 6 | `/speckit-plan` | Yes | Define technical implementation |
| 7 | `/speckit-checklist` | Recommended | Validate requirements quality |
| 8 | `/speckit-tasks` | Yes | Create actionable tasks |
| 9 | `/speckit-analyze` | Recommended | Check cross-artifact consistency |
| 10 | `/speckit-implement` | Yes | Implement the approved tasks |
| 11 | `/speckit-converge` | Recommended | Find and close remaining gaps |

## Existing Project Versus New Project

### New Azure Workload

Use the complete workflow starting with Constitution and Azure Interview.

### Existing Azure Workload

Use the same workflow. During the interview, classify the workload as one of:

- `brownfield`
- `migration`
- `extension`

Do not classify existing Azure resources as newly managed resources without
confirming:

- Full Azure resource ID
- Current owner
- Intended lifecycle
- Whether modification is allowed
- Whether the resource remains externally managed
- Whether import into the IaC state is required and approved

## Updating the Extension

Inspect the installed extension:

```powershell
specify extension info azure-interview
```

To move to a later release, review its release notes and follow the upgrade
instructions published with that version.

Do not replace a working version automatically in a production IaC repository.
Test the new version in a separate Spec Kit project first.

## Troubleshooting

### Extension URL Is Treated as a Catalog Name

Incorrect:

```powershell
specify extension add `
    https://github.com/RobertAgterhuis/speckit-azure-interview.git
```

Correct:

```powershell
specify extension add azure-interview `
    --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.5.0.zip
```

The `--from` value must point to a ZIP, tar.gz, or tgz archive.

### Command Is Unknown

Verify:

```powershell
specify extension list
specify extension info azure-interview
```

Then inspect the integration-specific generated command or skill directory.

For Claude:

```powershell
Get-ChildItem .\.claude\skills -Directory |
    Select-Object Name
```

Expected:

```text
speckit-azure-interview-run
```

Restart the AI agent after installing or updating the extension.

### Validator Cannot Import `jsonschema`

Activate the project virtual environment and install the runtime dependency:

```powershell
.\.venv\Scripts\Activate.ps1

python -m pip install `
    -r .\.specify\extensions\azure-interview\requirements-runtime.txt
```

### Interview Resumes Old Context

Inspect:

```powershell
Get-ChildItem .\.specify\discovery
```

The extension intentionally resumes an existing interview. Archive or remove
old discovery artifacts only when you explicitly intend to start a separate
workload interview.

## Further Reading

- [Spec Kit Azure Interview](https://github.com/RobertAgterhuis/speckit-azure-interview)
- [Spec Kit Azure Interview releases](https://github.com/RobertAgterhuis/speckit-azure-interview/releases)
- [Original GitHub Spec Kit](https://github.com/github/spec-kit)
- [GitHub Spec Kit releases](https://github.com/github/spec-kit/releases)
- [AVM Spec Kit guidance](https://azure.github.io/Azure-Verified-Modules/experimental/ai-assisted-sol-dev/spec-kit/)
- [AVM Spec Kit example](https://azure.github.io/Azure-Verified-Modules/experimental/ai-assisted-sol-dev/spec-kit/avm-example/)
- [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/)
- [Codex Integration](docs/CODEX.md)
- [GitHub Copilot Integration](docs/COPILOT.md)
- [Hermes Agent Integration](docs/HERMES.md)

## Generate and Review the Intended Design

After the Azure architecture interview is complete and
`.specify/discovery/azure-context.json` has been validated, run:

    /speckit.azure-interview.design

The command generates:

- `.specify/design/azure-design-model.json`;
- `.specify/design/azure-design-overview.md`;
- `.specify/design/azure-design-overview.svg`;
- `.specify/design/azure-design-overview.drawio`.

The JSON model is the machine-readable design contract. The Markdown, SVG, and
Draw.io files provide human-reviewable visualizations of the same architecture.

A newly generated design uses:

    designStatus: intended
    reviewStatus: unreviewed

Review the design before continuing to specification or implementation. Confirm
planned resources, reused resources, ownership boundaries, hub peering, central
egress, private DNS, private endpoints, and diagnostic settings.

To replace an existing set after explicit approval, run:

    /speckit.azure-interview.design --overwrite

See [Azure Intended Design](docs/AZURE-DESIGN.md) for the complete workflow and
security boundaries.
