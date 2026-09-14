---
description: "Generate a reviewable intended-state Azure architecture design after the interview"
---

# Azure Intended Design

Generate an intended-state Azure architecture model and visual review artifacts
from a completed and confirmed Azure interview context.

This command generates design evidence. It does not inspect deployed Azure
resources, execute deployment operations, or prove that the intended
architecture has been implemented.

This command is an add-on to Spec Kit. It must not replace, wrap, override, or
modify any Spec Kit Core command, template, script, configuration, or artifact.

## User Input

```text
$ARGUMENTS
```

Consider the user input before starting. It may contain explicit input paths,
output paths, or overwrite approval.

## Prerequisites

Before generating a design:

1. Confirm that the current directory is a Spec Kit project containing
   `.specify`.
2. Confirm that the completed interview context exists at:

   ```text
   .specify/discovery/azure-context.json
   ```

3. Confirm that the interview has status `complete`.
4. Confirm that the interview is specification-ready.
5. Confirm that required fields contain confirmed information.
6. Do not convert assumptions, inferred values, or unconfirmed inventory
   evidence into intended design facts.

If the interview context is incomplete or invalid, stop and explain what must
be resolved through the Azure interview.

## Canonical Outputs

Generate these artifacts under `.specify/design`:

```text
.specify/design/azure-design-model.json
.specify/design/azure-design-overview.md
.specify/design/azure-design-overview.svg
.specify/design/azure-design-overview.drawio
```

The artifacts have distinct purposes:

- `azure-design-model.json` is the validated machine-readable intended-design
  contract.
- `azure-design-overview.md` is the human-review document and contains the
  Mermaid representation.
- `azure-design-overview.svg` is a standalone read-only visual artifact.
- `azure-design-overview.drawio` is the editable diagrams.net artifact.

## Required Status

Every newly generated design must use:

```text
designStatus: intended
reviewStatus: unreviewed
```

Never describe an unreviewed design as approved.

Never describe intended-state design output as deployed, discovered, observed,
verified, or as-built Azure state.

## Safe Generation

Use the packaged generator:

```text
scripts/python/generate_azure_design.py
```

Run it from the consumer Spec Kit project.

Example:

```bash
python .specify/extensions/azure-interview/scripts/python/generate_azure_design.py
```

On PowerShell:

```powershell
python `
    .\.specify\extensions\azure-interview\scripts\python\generate_azure_design.py
```

Only use `--overwrite` when the user explicitly approves replacing every
existing intended-design artifact.

Do not partially overwrite the design artifact set. Preflight all output paths
before writing any artifact.

## Design Interpretation

The generator may map confirmed interview information into:

- existing and planned resources;
- workload and platform ownership;
- hub-and-spoke networking;
- subnets;
- hub peering;
- central egress;
- private DNS resolution;
- private endpoints;
- diagnostic settings;
- resource dependencies.

Every relationship endpoint must reference a node in the generated model.

Existing resources remain subject to their recorded ownership and modification
boundaries.

## Human Review

After generation:

1. Present the artifact paths.
2. State that the design is intended and unreviewed.
3. Ask the user to review planned resources.
4. Ask the user to review reused existing resources.
5. Ask the user to review ownership and modification boundaries.
6. Ask the user to review network address spaces, subnets, peering, egress,
   DNS, and private endpoint paths.
7. Ask exactly one next confirmation question.

Do not start implementation merely because generation succeeded.

Implementation may proceed only after explicit human approval has been recorded.

## Final Response

Report:

- generation status;
- source context path;
- model path;
- Markdown overview path;
- SVG path;
- Draw.io path;
- design status;
- review status;
- overwrite performed: `Yes` or `No`;
- exactly one next review or confirmation question.
