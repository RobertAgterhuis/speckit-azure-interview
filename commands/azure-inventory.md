---
description: "Collect scoped read-only Azure inventory evidence before or during the Azure interview"
---

# Azure Inventory Discovery

Collect optional, subscription-scoped, read-only Azure inventory evidence for
use during the Azure architecture interview.

This command is an add-on to Spec Kit. It must not modify, replace, wrap, or
override any Spec Kit Core command, template, script, configuration, or
artifact.

## User Input

```text
$ARGUMENTS
```

Treat user input as optional initial scope information. It may contain a tenant
ID, subscription ID, intended output path, or a request to refresh existing
inventory evidence.

## Purpose

This command reduces manual brownfield discovery by collecting basic Azure
resource metadata through Azure Resource Graph.

The resulting artifact is evidence only. Its status is `unconfirmed`, and it
must not be merged automatically into `azure-context.json`.

The Azure architecture interview remains responsible for:

- Presenting relevant findings to the user
- Resolving conflicts with user or repository evidence
- Confirming ownership and lifecycle intent
- Confirming whether discovered resources may be modified
- Recording approved facts and decisions
- Applying the normal specification-readiness gate

## Non-Negotiable Safety Rules

1. Azure inventory discovery is optional.
2. Obtain explicit approval before executing the collector.
3. Confirm the intended tenant and subscription before execution.
4. Require one explicit subscription ID for every collector invocation.
5. Never perform a tenant-wide or multi-subscription scan implicitly.
6. Execute only the packaged read-only inventory collector.
7. Do not create, modify, deploy, import, move, or delete Azure resources.
8. Do not execute deployments, What-If operations, or write operations.
9. Do not retrieve secrets, keys, certificates, or access tokens.
10. Do not query resource configuration payloads through the baseline inventory
    query.
11. Do not treat discovered resources as approved for reuse or modification.
12. Do not treat a resource name as proof of ownership or purpose.
13. Do not silently replace an existing inventory artifact.
14. Do not commit inventory evidence without explicit user review.
15. Stop when the active Azure context differs from the approved scope.
16. Preserve unknown ownership, lifecycle, and modification permissions as
    unknown.

## Prerequisites

Before proposing collection:

1. Confirm that the current directory is a Spec Kit project.
2. Confirm that `.specify/` exists.
3. Locate the installed `azure-interview` extension.
4. Confirm that Python can run the packaged collector.
5. Confirm that Azure CLI is installed.
6. Confirm that the Azure CLI session is authenticated.
7. Confirm the tenant and subscription intended for discovery.
8. Explain that the collector uses `az account show` and a
   subscription-scoped `az graph query`.
9. Explain that collected evidence remains unconfirmed.
10. Obtain explicit approval for this exact read-only collection.

Do not interpret prior approval for another Azure command as approval for this
collection.

## Approval Interaction

Ask exactly one approval question before execution.

The question must identify:

- Tenant ID when supplied
- Subscription ID
- Commands that will be used
- Evidence output path
- Whether an existing artifact will be overwritten

A valid approval must be explicit. `GROEN` may confirm the immediately preceding
collection proposal only when that proposal includes the exact tenant,
subscription, commands, output path, and overwrite behavior.

## Artifact Location

The default project-local artifact is:

```text
.specify/discovery/azure-inventory.json
```

The artifact:

- Uses the packaged `azure-inventory.schema.json` contract
- Contains only baseline resource metadata
- Records the tenant and subscription scope
- Records the retrieval timestamp
- Records the Resource Graph query
- Records `readOnly` as `true`
- Records `evidenceStatus` as `unconfirmed`
- Must remain inside `.specify/discovery/`
- Must not be merged automatically into the confirmed interview context

Use `--overwrite` only when the user explicitly approved replacing the existing
artifact.

## Collector Invocation

Locate the installed collector without modifying the extension installation.

A typical PowerShell invocation is:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\collect_azure_inventory.py `
  --subscription <confirmed-subscription-id> `
  --tenant <confirmed-tenant-id> `
  --approve-read-only
```

Omit `--tenant` only when the user approved validating solely against the
specified subscription and understands that the active tenant will still be
recorded.

To replace an existing artifact after explicit approval:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\collect_azure_inventory.py `
  --subscription <confirmed-subscription-id> `
  --tenant <confirmed-tenant-id> `
  --approve-read-only `
  --overwrite
```

Do not substitute names, aliases, `current`, wildcards, or generated values for
tenant and subscription UUIDs.

## Result Review

After successful collection:

1. Report the exact output path.
2. Report the tenant and subscription recorded in the artifact.
3. Report the resource count.
4. State clearly that the evidence remains unconfirmed.
5. Summarize discovered resource types without assigning lifecycle intent.
6. Ask the user whether the scope and high-level findings are correct.
7. Continue reconciliation through the Azure architecture interview.
8. Never infer permission to modify a discovered resource.

If Azure evidence conflicts with interview or repository evidence, preserve both
statements and ask the user which is authoritative.

## Failure Behaviour

Stop without writing or replacing the artifact when:

- The directory is not a Spec Kit project
- Approval is missing
- Tenant or subscription identifiers are invalid
- Azure CLI is unavailable
- Azure CLI authentication is missing
- The active subscription does not match
- The active tenant does not match when tenant scope was supplied
- Azure Resource Graph returns invalid data
- A record falls outside the approved subscription
- Schema or semantic validation fails
- The output path falls outside `.specify/discovery/`
- The output already exists and overwrite was not explicitly approved

Report the failure and the single corrective action required. Do not weaken the
safety boundary to continue.

## Completion Response

Report:

- Collection status
- Tenant ID
- Subscription ID and name
- Resource count
- Evidence timestamp
- Artifact path
- Evidence status: `unconfirmed`
- Overwrite performed: `Yes` or `No`
- Exactly one next confirmation question

Do not declare the Azure architecture interview ready merely because inventory
collection succeeded.

## Topology Evidence

When topology evidence is present:

1. Report the topology relationship count.
2. Summarize relationship counts by `relationshipType`.
3. Summarize targets classified as `in-scope`, `external-subscription`, or
   `unresolved`.
4. State that every relationship remains unconfirmed evidence.
5. Ask the user to verify architectural meaning, ownership, lifecycle intent,
   and modification boundaries.

Only query the explicitly approved subscription. Record a controlled reference
when a target is classified as `external-subscription`, but never query a
referenced external subscription. Do not infer reachability, data flow,
ownership, permission, or intended reuse from a discovered relationship.
