# Azure Intended Design Review

Azure Intended Design Review records an explicit human approval or rejection
of one exact intended-state Azure architecture design.

The review is a governance checkpoint between design generation and Specify.
It does not deploy resources, inspect deployed Azure state, or grant Azure
permissions.

## Lifecycle Position

The intended workflow is:

1. Establish the project Constitution.
2. Optionally collect Azure inventory evidence.
3. Complete and confirm the Azure Interview.
4. Generate the Azure Intended Design.
5. Record the Azure Intended Design Review.
6. Continue to Specify only when implementation is authorized.

A newly generated design starts with:

```text
designStatus: intended
reviewStatus: unreviewed
```

The review command changes only `reviewStatus`. The design remains
`designStatus: intended` because approval does not prove deployment.

## AI Command

Invoke this command from a supported AI assistant:

```text
/speckit.azure-interview.design-review
```

For Codex skill-based installations, use:

```text
$speckit-azure-interview-design-review
```

Do not type the slash command directly into PowerShell. Slash commands and
skills are interpreted by the configured AI integration.

## Implementation

The packaged executable is:

```text
scripts/python/review_azure_design.py
```

The review record is validated against:

```text
templates/azure-design-review.schema.json
```

Install the runtime dependencies before direct execution:

```powershell
python -m pip install `
    -r .\.specify\extensions\azure-interview\requirements-runtime.txt
```

## Prerequisites

Before recording a review:

- run from the consumer Spec Kit project;
- confirm that the project contains `.specify`;
- confirm that `.specify/design/azure-design-model.json` exists;
- confirm that the design validates against `azure-design.schema.json`;
- inspect the Markdown, SVG, and Draw.io architecture views;
- resolve whether the decision is `approved` or `rejected`;
- identify the human reviewer;
- collect actionable findings when rejecting the design.

Approval must never be inferred from silence, an earlier design request, or
the successful generation of artifacts.

## Supported Decisions

Exactly two terminal decisions are supported.

### Approved

An approved review:

- requires an explicit human reviewer;
- permits no unresolved findings;
- sets `reviewStatus` to `approved`;
- sets `implementationAuthorized` to `true`.

Approval means that the reviewed intended design may progress to the next
documented workflow stage. It does not perform implementation.

### Rejected

A rejected review:

- requires an explicit human reviewer;
- requires at least one actionable finding;
- sets `reviewStatus` to `rejected`;
- sets `implementationAuthorized` to `false`.

Rejected designs must not progress to implementation. Address the findings,
regenerate or correct the intended design, and perform a new explicit review.

Conditional approval is intentionally unsupported. A design with unresolved
conditions must be rejected with actionable findings.

## Canonical Artifacts

The review creates these artifacts:

| Artifact | Purpose |
| --- | --- |
| `.specify/design/azure-design-review.json` | Machine-readable terminal review record |
| `.specify/design/azure-design-review.md` | Human-readable review summary |

The same transaction updates these design artifacts:

| Artifact | Synchronized change |
| --- | --- |
| `.specify/design/azure-design-model.json` | Records the terminal `reviewStatus` |
| `.specify/design/azure-design-overview.md` | Displays the terminal review status |
| `.specify/design/azure-design-overview.svg` | Displays the terminal review status |
| `.specify/design/azure-design-overview.drawio` | Displays the terminal review status |

All six artifacts represent one synchronized review result.

## Design Digest

The JSON review contains a lowercase SHA-256 digest of the final reviewed
design model.

The digest binds the decision to the exact serialized design that was
approved or rejected:

```json
{
  "designDigest": {
    "algorithm": "sha256",
    "value": "<64 lowercase hexadecimal characters>"
  }
}
```

Any later modification to the design model changes its digest and invalidates
the recorded review relationship. The design must then be reviewed again.

## Approval Example

Run from the consumer project:

```powershell
python `
    .\.specify\extensions\azure-interview\scripts\python\review_azure_design.py `
    --decision approved `
    --reviewer "Robert Agterhuis" `
    --comment "Architecture approved for implementation."
```

Expected control values:

```text
reviewStatus: approved
implementationAuthorized: true
```

Approval cannot contain `--finding` arguments.

## Rejection Example

```powershell
python `
    .\.specify\extensions\azure-interview\scripts\python\review_azure_design.py `
    --decision rejected `
    --reviewer "Robert Agterhuis" `
    --finding "Confirm the production subnet address space." `
    --finding "Resolve the private DNS ownership boundary." `
    --comment "Revise the intended design and submit it for review again."
```

Expected control values:

```text
reviewStatus: rejected
implementationAuthorized: false
```

Repeat `--finding` for every independently actionable issue.

## Overwrite Protection

An existing terminal review is protected.

The implementation refuses to replace
`.specify/design/azure-design-review.json` or
`.specify/design/azure-design-review.md` unless `--overwrite` is supplied.

Use `--overwrite` only after the user explicitly authorizes replacement:

```powershell
python `
    .\.specify\extensions\azure-interview\scripts\python\review_azure_design.py `
    --decision approved `
    --reviewer "Robert Agterhuis" `
    --comment "Re-reviewed after the intended design changed." `
    --overwrite
```

Overwrite authorization applies only to this synchronized review transaction.
It does not authorize changes outside `.specify/design`.

## Transactional Publication

Before publication, the implementation:

1. validates all input and output paths;
2. validates the unreviewed design;
3. applies the explicit decision;
4. validates the reviewed design;
5. validates the review JSON;
6. verifies the design digest;
7. renders Markdown, SVG, and Draw.io outputs;
8. validates the XML artifacts;
9. stages the complete artifact set.

The staged files are then published as one transaction. If replacement fails,
the implementation restores previously replaced artifacts. It does not
intentionally leave a partially updated review set.

## Security Boundaries

The review operation:

- accepts only `approved` or `rejected`;
- requires a non-empty reviewer identity;
- requires UTC review timestamps;
- constrains artifacts to `.specify/design`;
- requires unique artifact paths;
- safely escapes Markdown and XML content;
- validates relationship endpoints through the design schema;
- performs no Azure write operations;
- does not prove deployed Azure state;
- does not convert intended state into as-built evidence.

`implementationAuthorized: true` is a workflow control value. It is not an
Azure RBAC assignment, deployment credential, or technical enforcement grant.

## Verification

Inspect the machine-readable review:

```powershell
Get-Content `
    .\.specify\design\azure-design-review.json
```

Inspect the human-readable review:

```powershell
Get-Content `
    .\.specify\design\azure-design-review.md
```

Confirm the synchronized design status:

```powershell
(
    Get-Content `
        .\.specify\design\azure-design-model.json `
        -Raw |
    ConvertFrom-Json
).reviewStatus
```

Confirm that the review contains:

- the expected reviewer;
- the expected UTC timestamp;
- the intended terminal decision;
- the correct `implementationAuthorized` value;
- the SHA-256 design digest;
- all rejection findings, when applicable.

## Troubleshooting

### The design model cannot be found

Run the intended-design generator first and confirm that this file exists:

```text
.specify/design/azure-design-model.json
```

### Approval is rejected because findings exist

Approval cannot contain unresolved findings. Remove the `--finding` arguments
only after the human reviewer confirms that the issues have been resolved.
Otherwise record a rejected decision.

### Rejection is rejected because no finding exists

Supply at least one actionable `--finding`. A rejection without an explanation
is not an adequate review record.

### A review artifact already exists

Do not delete it silently. Confirm whether the existing decision must remain.
Use `--overwrite` only after explicit replacement approval.

### The recorded digest no longer matches

The intended-design model changed after review. Treat the previous review as
invalid for the modified design and perform a new explicit review.

### Publication fails

The implementation attempts rollback. Inspect all six synchronized artifacts
before retrying and confirm that they reflect one consistent review state.

## Next Stage

When `reviewStatus` is `approved` and `implementationAuthorized` is `true`,
continue to Specify.

When `reviewStatus` is `rejected`, address the findings before progressing.
