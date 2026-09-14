# Azure Intended Design

The Azure Intended Design feature converts a completed and confirmed Azure
interview context into reviewable intended-state architecture artifacts.

It does not inspect deployed Azure resources and does not prove that the
architecture has been implemented.

## Workflow Position

Use the design command after the Azure architecture interview and before
implementation:

1. Optionally collect Azure inventory evidence.
2. Complete the Azure architecture interview.
3. Confirm the interview and generate `azure-context.json`.
4. Generate the intended design.
5. Review and approve or reject the intended design.
6. Continue with specification, planning, tasks, and implementation.
7. Later compare the approved design with deployed Azure state using a separate
   verification workflow.

## Command

Run:

    /speckit.azure-interview.design

The generated Copilot skill is:

    speckit-azure-interview-design

## Prerequisites

The current directory must be a Spec Kit consumer project containing:

    .specify
    .specify/discovery/azure-context.json

The interview context must:

- conform to the Azure context schema;
- have interview status `complete`;
- be specification-ready;
- contain no unresolved required questions;
- contain no blocking assumptions;
- contain confirmed ownership and modification boundaries.

Unconfirmed Azure inventory evidence must first be reconciled through the
interview. The generator must not silently promote inventory observations into
confirmed design facts.

## Generated Artifacts

The generator creates four synchronized artifacts:

| Artifact | Purpose |
| --- | --- |
| `.specify/design/azure-design-model.json` | Validated machine-readable intended-design contract |
| `.specify/design/azure-design-overview.md` | Human-review document with Mermaid diagram |
| `.specify/design/azure-design-overview.svg` | Standalone read-only architecture visual |
| `.specify/design/azure-design-overview.drawio` | Editable diagrams.net architecture visual |

All artifacts describe the same intended architecture.

## Status Model

A newly generated design uses:

    designStatus: intended
    reviewStatus: unreviewed

`intended` means the architecture is proposed from confirmed interview input.

`unreviewed` means a human has not yet approved the generated interpretation.

Neither status proves deployed Azure state.

## Existing and Planned Resources

The generated diagrams distinguish resource lifecycle state:

- Blue resources already exist and are intended for reuse.
- Yellow resources are planned and require implementation.
- Existing resources retain their recorded ownership and modification
  boundaries.
- A relationship represents intended connectivity or dependency, not observed
  runtime traffic.

## Supported Relationships

The initial design generator represents confirmed relationships including:

- hub-to-spoke peering;
- spoke-to-subnet containment;
- central firewall egress;
- private DNS resolution;
- private endpoint integration;
- diagnostic settings to a central workspace.

Every relationship source and target must reference a valid node in the design
model.

## Running the Generator Directly

From the consumer Spec Kit project, run the packaged generator:

    python .specify/extensions/azure-interview/scripts/python/generate_azure_design.py

On PowerShell:

    python `
        .\.specify\extensions\azure-interview\scripts\python\generate_azure_design.py

Use custom paths only when they remain inside the permitted project
directories.

Display all options with:

    python `
        .\.specify\extensions\azure-interview\scripts\python\generate_azure_design.py `
        --help

## Overwrite Protection

The generator refuses to replace an existing model, Markdown overview, SVG, or
Draw.io artifact unless `--overwrite` is provided.

Before writing anything, it checks all four output paths. This prevents partial
replacement of a previously reviewed artifact set.

Only use:

    --overwrite

after the user explicitly approves replacement of all existing intended-design
artifacts.

## Review Checklist

Before approving the intended design, confirm:

- every planned resource is required;
- every reused resource is correctly identified;
- resource ownership is correct;
- modification boundaries are preserved;
- regions and subscription scope are correct;
- address spaces and subnet prefixes are correct;
- hub peering is correct;
- central egress is correct;
- private DNS resolution is correct;
- private endpoints connect to the intended subnet;
- diagnostic settings connect to the intended workspace;
- assumptions remain visibly identified and are not represented as facts.

## Security Boundaries

The generator:

- performs no Azure deployment;
- performs no Azure Resource Manager write operation;
- does not change inventory evidence;
- does not modify the interview context;
- constrains input to project discovery JSON;
- constrains outputs to the project design directory;
- validates output against JSON Schema;
- validates unique node and relationship identifiers;
- validates every relationship endpoint;
- escapes untrusted content in Markdown, Mermaid, SVG, XML, and Draw.io;
- writes artifacts atomically;
- requires explicit overwrite approval.

## Failure Handling

Generation stops when:

- the current directory is not a Spec Kit project;
- the context is missing or invalid;
- the interview is incomplete;
- required confirmation is missing;
- an output path leaves the design directory;
- an output artifact already exists without overwrite approval;
- schema validation fails;
- semantic validation fails.

A failed generation must not be treated as an approved or complete design.

## Future As-Built Verification

The intended design is the review checkpoint before implementation.

A separate future verification command should collect deployed state after
implementation and compare it with the approved design. That later workflow
must report matched resources, missing resources, unexpected resources, and
configuration drift without rewriting the intended-design record.