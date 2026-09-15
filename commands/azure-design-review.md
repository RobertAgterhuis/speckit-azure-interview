---
description: "Record an explicit human approval or rejection of an intended-state Azure design"
---

# Azure Intended Design Review

Review one generated intended-state Azure architecture and record an explicit
human approval or rejection.

This command records review evidence. It does not prove deployed Azure state,
inspect Azure resources, deploy infrastructure, or perform Azure write
operations.

This command is an add-on to Spec Kit. It must not replace, wrap, override, or
modify any Spec Kit Core command, template, script, configuration, or artifact.

## User Input

```text
$ARGUMENTS
```

Consider the user input before starting. It may contain:

- the explicit review decision;
- the human reviewer's identity;
- rejection findings;
- an optional review comment;
- explicit overwrite approval.

This is an AI-assistant command. Invoke
`/speckit.azure-interview.design-review` from a supported AI assistant, not
from PowerShell or another operating-system shell.

## Prerequisites

Before recording a decision:

1. Confirm that the current directory is a Spec Kit project containing
   `.specify`.
2. Confirm that this intended-design model exists:

   ```text
   .specify/design/azure-design-model.json
   ```

3. Confirm that `designStatus` is `intended`.
4. Confirm that the current `reviewStatus` is `unreviewed`, unless the user
   explicitly authorizes `--overwrite`.
5. Present the intended-design overview to the user.
6. Review existing and planned resources.
7. Review ownership and modification boundaries.
8. Review network address spaces, subnets, peering, egress, DNS, private
   endpoints, diagnostics, and dependencies.
9. Obtain an explicit human approval or rejection.
10. Never infer approval from silence, prior conversation, design generation,
    or implementation intent.

## Supported Decisions

Only these decisions are supported:

```text
approved
rejected
```

Conditional approval is not supported.

For `approved`:

- unresolved findings are not permitted;
- `implementationAuthorized` becomes `true`;
- explicit human approval must be attributable to the named reviewer.

For `rejected`:

- at least one actionable finding is required;
- `implementationAuthorized` remains `false`;
- implementation must not begin.

## Canonical Review Outputs

The command creates:

```text
.specify/design/azure-design-review.json
.specify/design/azure-design-review.md
```

It also synchronizes the review status in:

```text
.specify/design/azure-design-model.json
.specify/design/azure-design-overview.md
.specify/design/azure-design-overview.svg
.specify/design/azure-design-overview.drawio
```

The JSON review record references the canonical design-model path and contains
a lowercase SHA-256 digest of the final reviewed design model. Any later design
change invalidates that recorded digest.

## Safe Execution

Use the packaged implementation:

```text
scripts/python/review_azure_design.py
```

Run it from the consumer Spec Kit project.

Approval example:

```bash
python .specify/extensions/azure-interview/scripts/python/review_azure_design.py \
  --decision approved \
  --reviewer "Human reviewer" \
  --comment "Reviewed and approved for implementation."
```

PowerShell:

```powershell
python `
    .\.specify\extensions\azure-interview\scripts\python\review_azure_design.py `
    --decision approved `
    --reviewer "Human reviewer" `
    --comment "Reviewed and approved for implementation."
```

Rejection example:

```bash
python .specify/extensions/azure-interview/scripts/python/review_azure_design.py \
  --decision rejected \
  --reviewer "Human reviewer" \
  --finding "Resolve the private DNS ownership boundary." \
  --finding "Confirm the production subnet address space."
```

Repeat `--finding` for multiple rejection findings.

Use `--overwrite` only when the user explicitly authorizes replacing an
existing terminal review. Overwrite approval applies to the synchronized review
transaction, not to unrelated files.

## Safety Boundaries

The review implementation:

- validates the design model before and after the status transition;
- validates `azure-design-review.schema.json`;
- binds the review to the final design through its SHA-256 digest;
- constrains review artifacts to `.specify/design`;
- rejects duplicate output paths;
- preflights existing terminal review artifacts;
- stages the synchronized artifact set before publication;
- rolls back replaced artifacts if publication fails;
- does not prove deployed Azure state;
- does not perform Azure write operations.

Approval authorizes progression within the documented Spec Kit workflow. It
does not grant Azure RBAC permissions or execute implementation.

## Final Response

Report:

- review operation status;
- decision;
- reviewer;
- reviewed UTC timestamp;
- design-model path;
- review JSON path;
- review Markdown path;
- design digest algorithm and value;
- implementation authorized: `Yes` or `No`;
- overwrite performed: `Yes` or `No`;
- exactly one next workflow question.

For an approved review, ask whether the user wants to continue to Specify.

For a rejected review, ask whether the user wants to address the first finding.
