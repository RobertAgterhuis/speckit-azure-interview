---
title: "Intended Design Review"
description: "Record an explicit human approval or rejection of one intended Azure design."
---

Record an attributable terminal review decision for one exact intended-state
Azure architecture.

The command does not query Azure, deploy resources, grant permissions, or prove
deployed Azure state.

## Command

Invoke from a supported AI assistant:

```text
/speckit.azure-interview.design-review
```

For a generated Codex skill, use:

```text
$speckit-azure-interview-design-review
```

Do not enter the AI command directly in PowerShell.

## Prerequisites

Before reviewing:

- confirm `.specify/design/azure-design-model.json` exists;
- inspect the Markdown, SVG, and Draw.io design artifacts;
- verify existing and planned resources;
- verify ownership and modification boundaries;
- verify networking, DNS, private endpoints, diagnostics, and dependencies;
- obtain an explicit human decision and reviewer identity.

## Decisions

The command supports only `approved` and `rejected`.

### Approved

Approval requires no unresolved findings and records:

```text
reviewStatus: approved
implementationAuthorized: true
```

### Rejected

Rejection requires at least one actionable finding and records:

```text
reviewStatus: rejected
implementationAuthorized: false
```

Conditional approval is not supported.

## Outputs

The command creates:

- `.specify/design/azure-design-review.json`;
- `.specify/design/azure-design-review.md`.

It synchronizes the review status across the design model, Markdown overview,
SVG, and Draw.io diagram.

The review JSON contains a lowercase SHA-256 digest of the final reviewed design
model.

## Direct execution

Approval example:

```powershell
python `
    .\.specify\extensions\azure-interview\scripts\python\review_azure_design.py `
    --decision approved `
    --reviewer "Human reviewer" `
    --comment "Architecture approved for implementation."
```

Rejection example:

```powershell
python `
    .\.specify\extensions\azure-interview\scripts\python\review_azure_design.py `
    --decision rejected `
    --reviewer "Human reviewer" `
    --finding "Confirm the production subnet address space."
```

Use `--overwrite` only after explicit authorization to replace an existing
terminal review.

## Next stage

Continue to Specify only when the review is `approved` and
`implementationAuthorized` is `true`.
