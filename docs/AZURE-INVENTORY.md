# Azure Inventory Discovery

Azure Inventory Discovery is an optional, read-only enrichment capability for
Spec Kit Azure Interview. It collects basic resource metadata from one approved
Azure subscription and stores it as unconfirmed evidence for later review.

It is designed primarily for brownfield, migration, and extension scenarios in
which existing Azure resources may affect the architecture.

## What It Does

The collector:

- Verifies the active tenant and subscription
- Queries Azure Resource Graph for one subscription
- Retains only an explicit metadata allowlist
- Validates the result against a JSON Schema
- Writes a project-local evidence artifact
- Marks all collected data as `unconfirmed`

The collector does not decide whether a resource should be reused, changed,
migrated, replaced, or ignored. Those decisions remain part of the interactive
Azure architecture interview.

## Safety Model

Inventory collection requires all of the following:

1. An initialized Spec Kit consuming project with a `.specify/` directory.
2. Azure CLI installed and authenticated.
3. One explicit subscription UUID.
4. An optional explicit tenant UUID.
5. User approval for the exact tenant, subscription, commands, output path, and
   overwrite behavior.
6. The `--approve-read-only` flag.

The collector uses `shell=False`, validates canonical UUIDs, scopes Resource
Graph to one subscription, rejects cross-subscription records, and applies a
local output allowlist.

It never performs deployments, What-If operations, resource changes, role
assignments, policy changes, or secret retrieval.

## Azure Permissions

The signed-in identity needs permission to read the intended subscription and
query Azure Resource Graph. The built-in Azure `Reader` role at subscription
scope is normally sufficient for baseline resource metadata.

The collector does not require Owner, Contributor, User Access Administrator,
Key Vault data-plane roles, or secret-reading permissions.

Apply least privilege and scope Reader access only where inventory discovery is
approved.

## Collected Fields

Each resource record contains only:

| Field | Purpose |
|---|---|
| `id` | Stable Azure resource ID |
| `name` | Resource display name |
| `type` | Azure resource type |
| `location` | Azure region or global location |
| `resourceGroup` | Containing resource group |
| `subscriptionId` | Verified subscription boundary |
| `kind` | Optional resource kind |
| `managedBy` | Optional managing resource ID |

Even if Azure returns more fields, the collector removes properties, identities,
tags, SKUs, plans, zones, extended locations, and other unexpected content before
the artifact is created.

## Evidence Artifact

The default output is:

```text
.specify/discovery/azure-inventory.json
```

The artifact records:

- Schema version
- `evidenceStatus` set to `unconfirmed`
- UTC collection timestamp
- Read-only evidence source
- Exact Resource Graph query
- Tenant and subscription scope
- Resource count
- Allowlisted resource metadata

The artifact must not be committed to source control until its content and
organizational data-handling requirements have been reviewed. In most consuming
projects, `.specify/` is already excluded from Git.

## Run Through the Agent Command

Use the generated integration-specific inventory command. The visible syntax
depends on the active Spec Kit integration. The command guides scope
confirmation, explicit approval, collection, and evidence review.

The canonical extension command is:

```text
speckit.azure-interview.inventory
```

## Direct PowerShell Invocation

From an initialized consuming project:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\collect_azure_inventory.py `
  --subscription <confirmed-subscription-id> `
  --tenant <confirmed-tenant-id> `
  --approve-read-only
```

The tenant argument may be omitted only when the user explicitly approves
subscription-only matching. The active tenant is still recorded in the output.

## Existing Artifact Protection

The collector does not replace an existing artifact by default. It stops before
contacting Azure when the destination already exists.

To refresh an artifact after explicit approval:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\collect_azure_inventory.py `
  --subscription <confirmed-subscription-id> `
  --tenant <confirmed-tenant-id> `
  --approve-read-only `
  --overwrite
```

The temporary file is created in the destination directory and flushed before
publication. Existing evidence is replaced only when `--overwrite` is supplied.

## Windows Behavior

On Windows, Azure CLI is commonly exposed through `az.cmd`. The collector first
tries `az` and safely retries `az.cmd` when the first launcher is unavailable.
Both attempts use an argument array with `shell=False`.

## Reconciliation During the Interview

Inventory evidence does not become confirmed architecture context automatically.
The interview must verify:

- Tenant and subscription scope
- Evidence age
- Resource relevance
- Resource ownership
- Lifecycle intent
- Modification permission
- Dependencies and prohibited changes

Only user-confirmed interpretations may be recorded as Azure-sourced facts in
`azure-context.md` and later in `azure-context.json`.

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Evidence validated and written successfully |
| `2` | Controlled execution, scope, validation, or output failure |

Argument parsing also uses the standard `argparse` exit code `2` for invalid or
missing arguments.

## Troubleshooting

### Current directory is not a Spec Kit project

Run the collector from an initialized consuming project containing `.specify/`.
Do not run it from the extension source repository unless that repository was
also intentionally initialized as a consuming project.

### Azure CLI executable was not found

Confirm Azure CLI is installed and available:

```powershell
az version
```

On Windows, the collector automatically retries `az.cmd` without enabling a
shell.

### Active subscription or tenant does not match

Inspect the minimized active context, confirm it with the user, and select the
approved subscription before retrying. A changed Azure context requires renewed
approval.

### Inventory already exists

Review the existing artifact. Use `--overwrite` only after explicit approval to
replace it. Without approval, choose a different JSON filename under
`.specify/discovery/`.

### Resource Graph is unavailable

Confirm that Azure CLI can invoke `az graph query` and that the identity can read
the approved subscription. Do not broaden permissions automatically.

### Schema validation rejects unexpected fields

The local allowlist should remove unexpected Azure fields before validation. A
failure indicates a collector or schema regression and must be fixed rather than
bypassed.

## Security and Privacy Guidance

- Review inventory before sharing it.
- Treat resource IDs and names as organizational information.
- Do not add secret-bearing fields to the baseline query.
- Do not infer permission from discoverability.
- Do not infer environment or criticality from naming alone.
- Do not weaken schema validation to accept uncontrolled payloads.
- Do not commit generated inventory evidence by default.

## Brownfield topology relationships

The optional `topology` object records a deterministic, deduplicated view of
selected Azure relationships. It contains `relationshipCount` and a
`relationships` array.

The collector supports these controlled relationship types:

- `vnet-contains-subnet`
- `vnet-peered-with-vnet`
- `subnet-associated-with-nsg`
- `subnet-associated-with-route-table`
- `private-endpoint-placed-in-subnet`
- `private-dns-zone-linked-to-vnet`

Every relationship contains a fixed `relationshipType`, `sourceResourceId`,
`sourceResourceType`, `targetResourceId`, `targetResourceType`, and
`targetScope`. ARM resource IDs are normalized for deterministic comparison and
duplicate relationships are removed.

`targetScope` has one of these values:

- `in-scope`: the target belongs to the approved subscription;
- `external-subscription`: the target references another subscription, which is
  recorded but never queried;
- `unresolved`: the target cannot safely be classified from its resource ID.

The `source.topologyQueries` array records the six controlled Resource Graph
queries used for the collection. The collector executes them as seven separate
Resource Graph query flows: one resource query and six topology queries. This
avoids unreliable large union queries and keeps each projection allowlisted.

Topology evidence remains `unconfirmed`. A discovered relationship does not
prove ownership, intended reuse, lifecycle intent, modification permission,
connectivity, traffic flow, DNS resolution, or deployment correctness.
