# Codex Integration

This guide explains how to use Spec Kit Azure Interview with the OpenAI Codex
CLI.

## Tested Configuration

Codex support was verified with:

| Component | Tested version |
|---|---|
| Codex CLI | `0.154.0` |
| GitHub Spec Kit CLI | `1.0.7.dev0` |
| Spec Kit Azure Interview | `0.1.1` |
| Operating system | Windows |
| Shell | PowerShell 7 |

Later compatible versions may also work. Check the relevant release notes when
upgrading any component.

## Integration Model

The current Spec Kit Codex integration uses the shared agent-skills convention:

```text
.agents/skills/
```

After installation, the Azure interview skill is generated at:

```text
.agents/skills/speckit-azure-interview-run/SKILL.md
```

The extension remains installed under:

```text
.specify/extensions/azure-interview/
```

This means:

- Spec Kit owns integration-specific skill generation.
- The extension provides the canonical command and runtime assets.
- Codex consumes the generated project-local skill.
- No global Codex skill installation is required.
- No Codex-specific adapter is required.

## Prerequisites

Install:

- Git
- Python 3.11 or later
- `uv`
- GitHub Spec Kit CLI
- OpenAI Codex CLI

Verify Codex:

```powershell
codex --version
```

Verify Spec Kit:

```powershell
specify --version
specify check
```

## Initialize a Codex Spec Kit Project

Run this from the repository that will consume the extension:

```powershell
specify init --here --integration codex --script ps
```

Spec Kit should report:

```text
Selected coding agent integration: codex
```

The project should contain:

```text
.agents/
.specify/
```

Verify the recorded integration:

```powershell
Get-Content .\.specify\integration.json
```

Expected integration values include:

```json
{
  "installed_integrations": [
    "codex"
  ],
  "integration": "codex",
  "default_integration": "codex"
}
```

## Install Spec Kit Azure Interview

Install the immutable release archive:

```powershell
specify extension add azure-interview `
    --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.8.0.zip
```

Spec Kit displays an untrusted-source warning because the extension is installed
outside the official extension catalog.

Review the source and confirm with `y` only when you trust:

```text
https://github.com/RobertAgterhuis/speckit-azure-interview
```

Verify the installed extension:

```powershell
specify extension list
specify extension info azure-interview
```

Expected canonical command:

```text
speckit.azure-interview.run
```

## Verify the Generated Codex Skill

```powershell
Get-ChildItem .\.agents\skills -Directory |
    Select-Object Name, FullName
```

Expected skill:

```text
speckit-azure-interview-run
```

Inspect its metadata:

```powershell
Get-Content `
    .\.agents\skills\speckit-azure-interview-run\SKILL.md `
    -TotalCount 15
```

Expected frontmatter includes:

```yaml
name: speckit-azure-interview-run
description: Conduct an adaptive Azure architecture interview before specification
```

## Install the Runtime Dependency

Create and activate a project-local virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the validator dependency:

```powershell
python -m pip install `
    -r .\.specify\extensions\azure-interview\requirements-runtime.txt
```

## Start Codex

Start Codex from the consuming project root:

```powershell
codex
```

Do not start Codex from the extension source repository.

## Establish the Constitution

For a new project, establish the project principles before the Azure interview:

```text
$speckit-constitution

Define the governing principles for an AVM-based Azure IaC solution. Require secure-by-default design, least privilege, private connectivity where appropriate, reusable modules, automated validation, documented ownership boundaries, and no deployment without review.
```

Review:

```text
.specify/memory/constitution.md
```

Do not continue while it contains only the initial placeholder values.

## Start the Azure Interview

Invoke the project-local skill using the Codex skill notation:

```text
$speckit-azure-interview-run

We need an AVM-based Bicep solution for a production workload that must integrate with an existing Azure landing zone. Start a new Azure architecture interview.
```

Codex should explicitly acknowledge that it is using:

```text
speckit-azure-interview-run
```

## Expected First-Turn Behavior

Codex should:

1. Read the generated interview skill.
2. Inspect the Spec Kit project structure.
3. Read the constitution.
4. Read the Markdown context template.
5. Read the JSON Schema.
6. Check whether an interview already exists.
7. Record only confirmed input.
8. Create or update `.specify/discovery/azure-context.md`.
9. Keep unknown values explicit.
10. Ask exactly one business-purpose question.

The first primary question should be equivalent to:

```text
What specific business capability or problem must this workload address?
```

Codex must not yet:

- Ask for hub-spoke details.
- Ask for subscription or resource names.
- Access Azure.
- Retrieve secrets.
- Generate Bicep or Terraform.
- Run a deployment or What-If operation.
- Create `azure-context.json`.
- Mark the interview ready for specification.

## File-Access Approvals

Codex may request approval when its sandbox cannot read or write the local
project.

Before approving, review:

- The exact command.
- The target paths.
- Whether access is read-only or write access.
- Whether the operation stays inside the project.
- Whether the command could access Azure or external systems.

Typical safe read-only checks include:

```text
Get-Location
rg --files
Test-Path
Get-Content
Get-Date
```

A normal interview write should be limited to:

```text
.specify/discovery/azure-context.md
.specify/discovery/azure-context.json
```

The JSON file should only be created at final readiness.

Prefer one-time approval during initial testing. Do not grant a broad permanent
approval merely to remove prompts.

## Continue the Interview

Answer the opening business-purpose question first. Later responses may answer
a numbered batch of two to four related questions. Partial answers are allowed;
unanswered numbers remain open.

Codex should continuously update:

```text
.specify/discovery/azure-context.md
```

It must track:

- Confirmed facts
- Requirements
- Decisions
- Assumptions
- Open questions
- Dependencies
- Prohibited changes
- Readiness blockers

If Codex finds an existing interview, it should resume it unless you explicitly
request and authorize a separate interview.

## Validate Readiness

When Codex reports that the interview is complete, validate the JSON artifact:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\validate_context.py `
    .\.specify\discovery\azure-context.json `
    --schema .\.specify\extensions\azure-interview\templates\azure-context.schema.json
```

Expected:

```text
VALID: <absolute-path-to-azure-context.json>
```

Do not continue when validation fails.

## Specification Handoff

After validation succeeds, invoke the core Spec Kit skill:

```text
$speckit-specify

Use .specify/discovery/azure-context.md and .specify/discovery/azure-context.json as authoritative discovery input. Preserve confirmed requirements, ownership boundaries, existing-resource lifecycle intent, constraints, and prohibited changes. Do not treat assumptions as facts and do not invent missing Azure details.
```

Continue with:

```text
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

Clarify and Checklist are optional. Analyze and Converge are recommended for
production Azure IaC.

## Smoke-Test Acceptance Criteria

Codex support is considered healthy when:

- Spec Kit initializes with `--integration codex`.
- `.agents/skills` contains the core Spec Kit skills.
- `.agents/skills/speckit-azure-interview-run/SKILL.md` exists.
- Codex activates the skill using `$speckit-azure-interview-run`.
- The first question addresses only the business capability or problem.
- Markdown discovery context is created.
- JSON is not created prematurely.
- No infrastructure code is generated during discovery.
- No Azure operation occurs without explicit approval.
- Unknown information is not silently invented.

## Troubleshooting

### `.codex/skills` Does Not Exist

This is expected with the tested Spec Kit integration.

Inspect:

```powershell
Get-ChildItem .\.agents\skills -Directory
```

The current integration uses `.agents/skills`, not `.codex/skills`.

### Codex Does Not Recognize the Skill

Confirm that you started Codex from the correct repository:

```powershell
Get-Location
Test-Path .\.agents\skills\speckit-azure-interview-run\SKILL.md
```

Exit and restart Codex after installing or updating the extension.

Invoke the skill explicitly:

```text
$speckit-azure-interview-run
```

### Spec Kit Reports That This Is Not a Project

Run Spec Kit commands from the consuming project root containing:

```text
.specify/
```

Do not run integration commands from the extension source repository.

### Codex Creates JSON Too Early

Stop the interview and report the behavior.

Before readiness, only this artifact should exist:

```text
.specify/discovery/azure-context.md
```

JSON creation requires all schema-required values and a complete readiness
assessment.

### The Constitution Contains Placeholders

Run:

```text
$speckit-constitution
```

Review the completed constitution before restarting or continuing the Azure
interview.

### Codex Requests Broad Filesystem Access

Reject the request and ask Codex to narrow it to the consuming project and the
specific required files.

Do not approve access to unrelated directories, credentials, or user-profile
content.

## Reporting Codex Issues

When reporting a Codex integration issue, include:

- Codex CLI version
- Spec Kit CLI version
- Extension version
- Operating system
- Shell
- Integration configuration from `.specify/integration.json`
- Skill invocation used
- Expected behavior
- Actual behavior
- Relevant sanitized output
- Whether the issue involved sandbox approval

Do not include secrets, tokens, tenant IDs, subscription IDs, or confidential
resource identifiers.

Open an issue:

<https://github.com/RobertAgterhuis/speckit-azure-interview/issues>

Start a discussion:

<https://github.com/RobertAgterhuis/speckit-azure-interview/discussions>

## Generate the Intended Azure Design

After the interview is complete and `azure-context.json` is validated, invoke:

    /speckit.azure-interview.design

The command creates the JSON design model, Markdown and Mermaid overview,
standalone SVG, and editable Draw.io diagram under `.specify/design`.

Treat the generated design as `intended` and `unreviewed`. Do not describe it as
approved or deployed.

Review the design with the user before specification or implementation. Preserve
confirmed ownership, existing-resource lifecycle intent, modification
boundaries, and unresolved assumptions.

Only pass `--overwrite` after the user explicitly approves replacement of the
complete design artifact set.

See [Azure Intended Design](AZURE-DESIGN.md) for the full review and safety
workflow.

## Review the Intended Azure Design

After generating and inspecting the intended architecture, invoke:

    $speckit-azure-interview-design-review

The review must represent an explicit human decision. Supported decisions are
`approved` and `rejected`. Conditional approval is not supported.

For approval, provide the named human reviewer and confirm that no unresolved
findings remain. The synchronized result must contain:

- `reviewStatus: approved`;
- `implementationAuthorized: true`.

For rejection, provide the named reviewer and at least one actionable finding.
The synchronized result must contain:

- `reviewStatus: rejected`;
- `implementationAuthorized: false`.

The review produces:

- `.specify/design/azure-design-review.json`;
- `.specify/design/azure-design-review.md`.

It also updates the model, Markdown overview, SVG, and Draw.io diagram. The
review JSON contains a lowercase SHA-256 digest that binds the decision to the
exact final design model.

Do not infer approval from prior conversation or from successful artifact
generation. Do not start implementation while `implementationAuthorized` is
`false`.

Use `--overwrite` only after the user explicitly approves replacing an
existing terminal review. The command does not deploy Azure resources, grant
permissions, or prove deployed Azure state.

See [Azure Intended Design Review](AZURE-DESIGN-REVIEW.md) for the full
decision and verification workflow.
