---
title: Getting Started
description: Install Spec Kit Azure Interview and begin structured Azure architecture discovery.
---

Spec Kit Azure Interview supplements GitHub Spec Kit with Azure-specific
inventory, interview, intended-design, and future verification stages.

## Prerequisites

Before installing the extension, confirm:

- Git is installed.
- Python 3.10 or newer is available.
- GitHub Spec Kit is installed.
- The consumer repository has been initialized with Spec Kit.
- The project contains a `.specify` directory.
- Azure CLI is available when inventory discovery is required.

## Install version 0.5.0

Install the immutable release archive:

    specify extension add azure-interview \
      --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.8.0.zip

On PowerShell:

    specify extension add azure-interview `
        --from https://github.com/RobertAgterhuis/speckit-azure-interview/archive/refs/tags/v0.8.0.zip

## Verify the installation

Run:

    specify extension list
    specify extension info azure-interview

The extension should expose three commands:

- `speckit.azure-interview.inventory`
- `speckit.azure-interview.run`
- `speckit.azure-interview.design`

## Recommended order

1. Establish the project Constitution.
2. Optionally collect read-only Azure inventory.
3. Complete the Azure architecture interview.
4. Generate and review the intended design.
5. Continue with Specify, Plan, Tasks, Analyze, and Implement.

## Human-control boundaries

Inventory evidence starts as `unconfirmed`.

Intended design output starts as `intended` and `unreviewed`.

Neither artifact proves deployed Azure state, and neither may bypass explicit
human review.

## Next steps

After installing v0.8.0, use the workflow that matches the available evidence:

1. Establish the project constitution and confirm the repository boundary.
2. Run Azure Inventory Discovery when an existing subscription must be
   examined.
3. Review inventory and topology evidence before treating it as confirmed.
4. Start the adaptive Azure architecture interview.
5. Generate the Azure Intended Design only after the readiness gate passes.
6. Complete Azure Intended Design Review with an attributable human decision.
7. Continue to Spec Kit `specify` only after the design is approved.

Continue with the [complete workflow](./workflow/). For existing Azure estates,
also read the [inventory command](./commands/inventory/) and
[inventory evidence contract](./artifacts/inventory-evidence/).
