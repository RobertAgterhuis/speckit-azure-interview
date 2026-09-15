---
title: Complete Workflow
description: The end-to-end Spec Kit Azure Interview lifecycle.
---

The Azure extension adds inventory discovery, architecture interviewing,
intended-design generation, and an explicit Design Review Decision to the
standard Spec Kit lifecycle.

1. Constitution
2. Azure Inventory Discovery (optional)
3. Azure Interview
4. Intended Design Review
5. Design Review Decision
6. Specify
7. Clarify (optional)
8. Plan
9. Checklist (optional)
10. Tasks
11. Analyze (recommended)
12. Implement
13. Converge until complete

## Azure extension commands

The Azure-specific stages use:

1. `/speckit.azure-interview.inventory` for optional read-only inventory.
2. `/speckit.azure-interview.run` for the architecture interview.
3. `/speckit.azure-interview.design` for intended-design generation.
4. `/speckit.azure-interview.design-review` for the explicit human decision.

## Adaptive interview batches

The interview begins with one focused business-purpose question. After that
purpose is confirmed, it asks numbered batches containing two to four closely
related, independent questions from one phase and one topic cluster.

The user can:

- answer by display number;
- answer only part of a batch;
- use `unknown`, `TBD`, `not applicable`, or `use existing`;
- define an explicit scope-wide answer;
- identify exceptions to a scope-wide rule.

After each response, the interview recomputes the next applicable questions.
It does not continue through a fixed questionnaire and does not repeat questions
already covered by confirmed facts or scope rules.

Approval, consent, security exceptions, destructive actions, overwrite
authorization, and resource-modification exceptions remain isolated protected
decisions.

The interview can hand off only after synchronized Markdown and JSON context
artifacts are published and the JSON artifact passes schema and semantic
validation.

## Control boundaries

Inventory evidence remains `unconfirmed` until reconciled during the interview.

A generated design remains `intended` and `unreviewed` until an attributable
human review decision is recorded.

Approval sets:

- `reviewStatus: approved`;
- `implementationAuthorized: true`.

Rejection sets:

- `reviewStatus: rejected`;
- `implementationAuthorized: false`;
- at least one actionable finding.

Only an approved review authorizes progression to Specify. Neither the intended
design nor its review proves deployed Azure state.
