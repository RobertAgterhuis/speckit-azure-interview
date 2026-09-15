---
title: "Testing"
description: "Automated tests, package validation, and live smoke testing."
---

This document describes how to validate the Spec Kit Azure Interview extension locally before committing or releasing changes.

## Prerequisites

Install:

- Python 3.10 or later
- GitHub Spec Kit
- PowerShell 7 or later
- Git
- Optional: Claude Code
- Optional: Hermes Agent

Run all repository checks from the repository root:

```powershell
Set-Location DRIVE:\REPOROOT\speckit-azure-interview
```

## Create the Python Environment

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` must be located in the repository root.

## Run the Complete Local Test Suite

Run these commands from the repository root:

```powershell
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m yamllint extension.yml .yamllint.yml .github
python -m pytest -q
```

All commands must complete successfully before a pull request is submitted.

## Apply Automatic Python Fixes

Ruff can automatically fix supported linting issues:

```powershell
python -m ruff check scripts tests --fix
```

Format the Python files when required:

```powershell
python -m ruff format scripts tests
```

Run the complete test suite again after applying fixes.

## Validate the Example Context

Validate the known-good fixture:

```powershell
python scripts/python/validate_context.py `
    tests/fixtures/valid-context.json
```

Expected result:

```text
Azure interview context is valid.
```

The process must return exit code `0`.

Check the exit code in PowerShell:

```powershell
$LASTEXITCODE
```

## Validator Exit Codes

| Exit code | Meaning |
|---:|---|
| `0` | The context is valid |
| `1` | The context violates the Azure interview schema or semantic rules |
| `2` | The validator could not execute, read the input, or process the schema |

Consumers may use these exit codes in scripts and CI pipelines.

## Structural Tests

The structural test suite verifies that:

- `extension.yml` contains the required metadata.
- The command uses the correct Spec Kit namespace.
- Every declared command, template, and script exists.
- Command frontmatter is valid.
- Required package files are present.
- Runtime and development dependencies are separated.
- Development-only files are excluded from installation.
- Business-purpose-first interview safeguards are present.
- The extension package contains no unresolved manifest placeholders.

Run only the structural tests:

```powershell
python -m pytest tests/test_extension_package.py -v
```

## Validator Tests

The validator tests cover:

- A valid interview context.
- Missing required properties.
- Unknown properties.
- Invalid lifecycle values.
- Invalid readiness declarations.
- Critical unvalidated assumptions.
- Duplicate identifiers.
- Invalid identifier formats.
- Invalid JSON Schema input.

Run only the validator tests:

```powershell
python -m pytest tests/test_validate_context.py -v
```

## Clean Installation Test

Use a separate test project. Do not install the extension into its own source repository for this test.

Create the test project:

```powershell
$ExtensionPath = "G:\PERSONAL\REPOS\speckit-azure-interview"
$TestProjectPath = "G:\PERSONAL\REPOS\speckit-azure-interview-test"

if (-not (Test-Path $TestProjectPath)) {
    New-Item -ItemType Directory -Path $TestProjectPath | Out-Null
}

Set-Location $TestProjectPath
```

Initialize Spec Kit for the integration being tested:

```powershell
specify init --here --integration claude --script ps
```

Install the local extension:

```powershell
specify extension add $ExtensionPath
```

Inspect the installation:

```powershell
specify extension list
specify extension info azure-interview
```

Confirm that the installed extension does not contain development-only files:

```powershell
Get-ChildItem .\.specify\extensions\azure-interview -Recurse |
    Select-Object FullName
```

The installed package should not contain:

- `.git`
- `.github`
- `.venv`
- `tests`
- `requirements-dev.txt`
- `pyproject.toml`
- `.yamllint.yml`
- `CONTRIBUTING.md`
- `SECURITY.md`

## Claude Code Smoke Test

Initialize or use a clean Claude test project.

Start Claude Code from that project:

```powershell
claude
```

Invoke the generated skill:

```text
/speckit-azure-interview-run We need an AVM-based Bicep solution that integrates with an existing Azure landing zone. Start a new Azure architecture interview.
```

Verify that the interview:

- Asks one primary question at a time.
- Starts with the specific business capability or problem.
- Does not immediately ask for architecture details.
- Creates or updates `.specify/discovery/azure-context.md`.
- Does not create deployable infrastructure code.
- Does not access Azure without explicit approval.
- Does not create the JSON artifact before all required values are confirmed.
- Tracks contradictions and unresolved decisions explicitly.

## Codex CLI Smoke Test

Create or use a dedicated Codex test project. Do not run the smoke test from the
extension source repository.

Initialize Spec Kit:

```powershell
$CodexTestPath = "G:\PERSONAL\REPOS\speckit-azure-interview-test-codex"

New-Item `
    -ItemType Directory `
    -Path $CodexTestPath `
    -ErrorAction SilentlyContinue |
    Out-Null

Set-Location $CodexTestPath

specify init --here --integration codex --script ps
```

Install the released extension:

```powershell
specify extension add azure-interview `
    --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.5.0.zip
```

Verify the generated skill:

```powershell
Test-Path `
    .\.agents\skills\speckit-azure-interview-run\SKILL.md
```

Expected:

```text
True
```

Start Codex:

```powershell
codex
```

Invoke the skill:

```text
$speckit-azure-interview-run

We need an AVM-based Bicep solution for a production workload that must integrate with an existing Azure landing zone. Start a new Azure architecture interview.
```

Verify that Codex:

- Explicitly activates or acknowledges `speckit-azure-interview-run`.
- Reads the project-local skill from `.agents/skills`.
- Reads the constitution and extension templates.
- Creates `.specify/discovery/azure-context.md`.
- Records only confirmed information.
- Keeps unknown values explicit.
- Asks exactly one business-purpose question first.
- Does not ask for architecture details in the first question.
- Does not generate infrastructure code.
- Does not perform Azure operations.
- Does not create `.specify/discovery/azure-context.json` prematurely.

After the first response, verify the discovery artifacts:

```powershell
Get-ChildItem .\.specify\discovery |
    Select-Object Name, Length, LastWriteTime

Test-Path .\.specify\discovery\azure-context.json
```

The JSON check must return:

```text
False
```

Codex may request project filesystem approval when its sandbox cannot access the
test repository. Review the exact command and paths and prefer one-time approval
for smoke testing.

See [Codex Integration](../integrations/codex/) for complete expected behavior and
troubleshooting.

## GitHub Copilot Structural Test

This test verifies Spec Kit integration and skill generation without requiring a
paid GitHub Copilot conversation.

Create a dedicated test project:

```powershell
$CopilotTestPath = "G:\PERSONAL\REPOS\speckit-azure-interview-test-copilot"

if (-not (Test-Path $CopilotTestPath)) {
    New-Item -ItemType Directory -Path $CopilotTestPath | Out-Null
}

Set-Location $CopilotTestPath
```

Initialize Spec Kit:

```powershell
specify init --here --integration copilot --script ps
```

Install the released extension:

```powershell
specify extension add azure-interview `
    --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.5.0.zip
```

Accept the expected external-source warning only after verifying the archive
URL.

Verify the extension:

```powershell
specify extension list
specify extension info azure-interview
```

Expected installation output includes:

```text
Spec Kit Azure Interview (v0.5.0)
1 agent skill(s) auto-registered
```

Verify the integration record:

```powershell
Get-Content .\.specify\integration.json
```

Expected integration values include:

```text
integration: copilot
invoke_separator: -
```

Verify the generated skill:

```powershell
Test-Path `
    .\.github\skills\speckit-azure-interview-run\SKILL.md
```

Expected:

```text
True
```

Inspect its frontmatter:

```powershell
Get-Content `
    .\.github\skills\speckit-azure-interview-run\SKILL.md `
    -TotalCount 15
```

Expected values include:

```yaml
name: speckit-azure-interview-run
description: Conduct an adaptive Azure architecture interview before specification
```

Confirm that the generated skill contains the critical safeguards:

```powershell
$CopilotSkill = `
    ".\.github\skills\speckit-azure-interview-run\SKILL.md"

Select-String `
    -Path $CopilotSkill `
    -Pattern `
        "Ask exactly one primary question per response",
        "specific business capability or problem",
        "Create JSON only when",
        "Do not generate deployable infrastructure code"
```

Every required safeguard must be found.

### Structural Acceptance Criteria

The structural test passes when:

- Spec Kit accepts `--integration copilot`.
- `.specify/integration.json` records `copilot`.
- The released extension installs successfully.
- Spec Kit auto-registers one extension skill.
- `.github/skills/speckit-azure-interview-run/SKILL.md` exists.
- The skill name and description are correct.
- The complete interview safeguards are present.

This test does not validate model behavior and should not be described as a
behavioral Copilot smoke test.

## GitHub Copilot Behavioral Test

This test requires access to a supported GitHub Copilot runtime.

Open the consuming test project in a Copilot surface that supports agent skills.
Request the skill explicitly:

```text
Use the /speckit-azure-interview-run skill.

We need an AVM-based Bicep solution for a production workload that must integrate with an existing Azure landing zone. Start a new Azure architecture interview.
```

Verify that Copilot:

- Activates or acknowledges the intended skill.
- Reads the project constitution and interview templates.
- Creates `.specify/discovery/azure-context.md`.
- Records only confirmed facts.
- Preserves unknown values.
- Asks exactly one business-purpose question first.
- Does not ask architecture questions in the first response.
- Does not generate Bicep or Terraform.
- Does not perform Azure operations.
- Does not create `.specify/discovery/azure-context.json` prematurely.

Record:

- Copilot product and surface
- Copilot version
- Selected model
- Spec Kit version
- Extension version
- Operating system
- First complete response
- Created artifact names
- Any unexpected behavior

Sanitize all test evidence before sharing it.

Until this behavioral test is completed successfully, Copilot support remains:

```text
Preview — structurally verified; behavioral testing requested
```

See [GitHub Copilot Integration](../integrations/copilot/) for detailed guidance.

## Hermes Smoke Test

Because Hermes may use a custom `HERMES_HOME`, first install the compatibility skill:

```powershell
Set-Location G:\PERSONAL\REPOS\speckit-azure-interview

.\scripts\powershell\Install-HermesSkillAdapter.ps1
```

Confirm that Hermes recognizes the skill:

```powershell
hermes skills list |
    Select-String "speckit-azure-interview-run"
```

Start Hermes with the skill preloaded from the test-project directory:

```powershell
Set-Location G:\PERSONAL\REPOS\speckit-azure-interview-test-hermes

hermes --skills speckit-azure-interview-run
```

Enter the workload request as ordinary language:

```text
We need an AVM-based Bicep solution that integrates with an existing Azure landing zone. Start a new Azure architecture interview.
```

Do not use a slash command unless the active Hermes version explicitly supports it.

Verify the same behavioral safeguards used for the Claude smoke test.

## Interview Artifact Checks

During an interview, the extension may maintain:

```text
.specify/discovery/azure-context.md
```

The machine-readable artifact should only be generated when it can satisfy the complete schema:

```text
.specify/discovery/azure-context.json
```

Validate the final JSON artifact:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\validate_context.py `
    .\.specify\discovery\azure-context.json `
    --schema .\.specify\extensions\azure-interview\templates\azure-context.schema.json
```

The interview is not ready for `/speckit.specify` unless this validation succeeds.

## Test Isolation

Always use disposable or dedicated test projects for integration testing.

Do not:

- Reuse production infrastructure repositories.
- Connect to Azure unless the test explicitly requires approved read-only discovery.
- Deploy resources during an interview smoke test.
- Store credentials, tokens, subscription identifiers, or secrets in fixtures.
- Commit generated discovery artifacts containing organizational information.

## Before Committing

Run:

```powershell
Set-Location DRIVE:\REPOROOT\\speckit-azure-interview

python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m yamllint extension.yml .yamllint.yml .github
python -m pytest -q
git status --short
```

Review every changed and untracked file before committing.

## Azure Inventory Tests

The Azure inventory implementation has a focused suite of **68 passed** tests
covering:

- Canonical tenant and subscription UUID validation
- Explicit `--approve-read-only` consent
- Active Azure context matching
- Shell-free command execution
- Windows `az.cmd` fallback
- Subscription-scoped Azure Resource Graph command construction
- Resource-response validation
- Cross-subscription rejection
- Local metadata allowlist enforcement
- Unconfirmed evidence generation
- UTC timestamp normalization
- JSON Schema and semantic validation
- Project-local output restrictions
- Atomic writes and explicit overwrite protection
- Rejection of existing output before Azure is contacted
- Complete collection-to-file orchestration
- Stable success and controlled-error exit codes

The live smoke test used an authenticated Windows Azure CLI session against one
approved sandbox subscription. It collected seven resources, validated the
artifact, retained only the eight approved metadata fields, and wrote
`.specify/discovery/azure-inventory.json` with `evidenceStatus` set to
`unconfirmed`.

Live testing must use a non-production or explicitly approved subscription.
Generated inventory evidence must not be committed without review.

## Azure Intended-Design Tests

The intended-design test suite validates:

- completed and confirmed Azure context requirements;
- deterministic architecture nodes and relationships;
- existing and planned lifecycle states;
- hub peering, subnet containment, central egress, and private DNS;
- private endpoint and diagnostic-setting relationships;
- JSON Schema validation;
- unique node and relationship identifiers;
- valid relationship endpoints;
- project-local input and output paths;
- overwrite preflight across all four artifacts;
- atomic JSON and text output;
- deterministic Mermaid rendering;
- valid and safely escaped SVG;
- editable and safely escaped Draw.io XML;
- command and extension package contracts.

Run the focused generator tests:

    python -m pytest tests/test_generate_azure_design.py -q

Run the package tests:

    python -m pytest tests/test_extension_package.py -q

Run the full suite:

    python -m pytest -q

A manual smoke test must also verify that:

- the Markdown preview renders the Mermaid diagram;
- the SVG opens independently;
- the Draw.io file opens in diagrams.net;
- all nodes and relationships are visible;
- existing and planned resources remain distinguishable;
- relationship labels do not obscure resource content;
- all four artifacts describe the same intended architecture.

The smoke test confirms rendering compatibility only. It does not approve the
design or verify deployed Azure state.

## Documentation and security validation

The repository validates the public documentation as part of the release
quality gate.

### Astro validation

Run the configured Astro checks before publication. Astro must report zero
errors, zero warnings and zero hints. The documentation build must generate
all configured static routes successfully.

The public-site contract additionally verifies that essential workflow,
inventory, interview, design-review and release information remains present in
the Starlight source pages.

### CodeQL validation

GitHub CodeQL provides the repository security-analysis gate. A documentation
or release change is not considered complete until the CodeQL workflow and the
other required GitHub Actions checks finish successfully.

### Live publication validation

After the Documentation workflow succeeds, verify routes independently:

- the homepage exposes the complete product workflow and current release;
- Getting Started exposes the active immutable installation version;
- command pages expose approvals, failure behavior and safety boundaries;
- artifact pages expose schemas, evidence status and limitations;
- every checked route returns HTTP 200;
- visible normalized page text contains the required route-specific content.

A successful build alone does not prove that the expected content is live.
Always bind the Documentation workflow run to the exact main commit being
verified.
