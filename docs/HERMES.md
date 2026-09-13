# Hermes Integration

## Overview

Spec Kit supports Hermes as an AI integration and generates skills under the
default user-profile location:

```text
%USERPROFILE%\.hermes\skills
```

Some Hermes installations use a custom profile through the `HERMES_HOME`
environment variable. In that configuration, Hermes loads categorized skills
from:

```text
%HERMES_HOME%\skills\<category>\<skill-name>\SKILL.md
```

When these locations differ, Spec Kit may successfully install an extension
without the active Hermes instance discovering its generated skill.

## Detect the Active Hermes Home

In PowerShell:

```powershell
$env:HERMES_HOME
hermes config path
hermes config env-path
```

Example:

```text
HERMES_HOME=E:\AI\Hermes
E:\AI\Hermes\config.yaml
E:\AI\Hermes\.env
```

## Verify the Spec Kit-Generated Skill

After initializing a Spec Kit project with the Hermes integration and installing
this extension, verify the generated skill:

```powershell
$GeneratedSkill = Join-Path `
    $env:USERPROFILE `
    ".hermes\skills\speckit-azure-interview-run\SKILL.md"

Test-Path $GeneratedSkill
```

Expected result:

```text
True
```

## Install the Compatibility Adapter

From the consuming Spec Kit project:

```powershell
$Adapter = `
    ".\.specify\extensions\azure-interview\scripts\powershell\Install-HermesSkillAdapter.ps1"

& $Adapter
```

The adapter:

- Reads the active `HERMES_HOME`.
- Validates the generated skill frontmatter.
- Installs the skill under the `devops` category.
- Refuses to overwrite differing content by default.
- Returns `Unchanged` when the installed content is already current.
- Creates a timestamped backup before a forced replacement.
- Prevents calculated paths from escaping the Hermes skills root.

## Update an Existing Hermes Skill

After updating or reinstalling the Spec Kit extension, refresh the active Hermes
copy:

```powershell
& $Adapter -Force
```

Review the returned backup path and SHA-256 hash.

Run it again without `-Force` to verify idempotency:

```powershell
& $Adapter
```

Expected status:

```text
Unchanged
```

## Custom Category

The default category is `devops`. A different lowercase category can be used:

```powershell
& $Adapter -Category "azure"
```

The category must contain only lowercase letters, numbers, and hyphens.

## Custom Source Skill

When Spec Kit generated the skill in a non-default location:

```powershell
& $Adapter `
    -SourceSkillPath "D:\GeneratedSkills\speckit-azure-interview-run\SKILL.md"
```

## Verify Hermes Registration

```powershell
hermes skills list |
    Select-String "speckit-azure-interview-run"
```

The skill should be reported as enabled and local.

## Start Hermes with the Skill Preloaded

Natural-language requests do not guarantee that smaller local models will
select the correct skill. Preload it explicitly:

```powershell
hermes --skills speckit-azure-interview-run
```

Then enter the workload description:

```text
We need an AVM-based Bicep solution for an internal production application.
It must integrate with an existing Azure landing zone. Start a new Azure
architecture interview.
```

Do not invoke the skill as a slash command. Hermes reserves slash commands for
its own interactive command interface.

## Expected First Interaction

The interview must:

- Confirm the current directory is a Spec Kit project.
- Read the extension instructions.
- Read the constitution when it exists.
- Check for existing discovery artifacts.
- Ask only for the specific business capability when that remains unclear.
- Avoid implementation, deployment, or Azure write operations.
- Avoid creating the JSON handoff artifact prematurely.

## Performance with Local Models

The complete interview skill, Spec Kit context, and Hermes tool catalog can
produce a substantial prompt. Smaller local models may take several minutes for
the first response.

A changing reasoning indicator means the model is still processing. Auxiliary
title-generation timeouts are separate from the interview execution.

For reliable behaviour:

- Preload only the required interview skill.
- Avoid activating unrelated skills.
- Use the strongest locally available instruction-following model.
- Keep the first workload prompt concise.
- Allow the first turn additional processing time.
- Resume an interrupted session instead of starting over when possible.

## Troubleshooting

### Skill Exists but Hermes Cannot Find It

Compare these locations:

```powershell
$DefaultSkillRoot = Join-Path $env:USERPROFILE ".hermes\skills"
$ActiveSkillRoot = Join-Path $env:HERMES_HOME "skills"

$DefaultSkillRoot
$ActiveSkillRoot
```

Run the compatibility adapter when they differ.

### Skill Is Listed but the Model Does Not Use It

Start Hermes with explicit skill preloading:

```powershell
hermes --skills speckit-azure-interview-run
```

### Hermes Invents a Command Such as `hermes agent run`

Stop the session. That command is not part of this extension. Restart Hermes
with the skill preloaded.

### Adapter Refuses to Overwrite

The active skill differs from the newly generated skill. Review both files, then
run:

```powershell
& $Adapter -Force
```

The adapter creates a timestamped backup before replacement.

### Extension Was Updated but Hermes Uses Old Instructions

Reinstall or update the extension in the consuming Spec Kit project, then rerun
the adapter with `-Force`.

## Upstream Compatibility Note

The adapter exists only for Hermes installations where the active
`HERMES_HOME` differs from the default path targeted by the Spec Kit Hermes
integration.

It does not modify Spec Kit Core or Hermes Core. When upstream integration
supports custom `HERMES_HOME` paths directly, the adapter can be retired without
changing the Azure interview command or its artifacts.