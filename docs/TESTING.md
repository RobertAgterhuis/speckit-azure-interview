# Testing Guide

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