---
description: "Conduct an adaptive Azure architecture interview before specification"
---

# Azure Architecture Interview

Conduct a structured and adaptive Azure architecture discovery interview before
the user runs the core Spec Kit specification workflow.

This command is an add-on to Spec Kit. It MUST NOT modify, replace, wrap, or
override any Spec Kit Core command, template, script, configuration, or artifact.

## User Input

```text
$ARGUMENTS
```

Treat the user input as optional initial context. It may contain a workload
description, repository path, architecture document, existing resource details,
or instructions about the intended Azure solution.

## Purpose

The command must reduce ambiguity before `/speckit.specify` by discovering and
recording:

- Business and workload requirements
- Greenfield, brownfield, migration, or extension context
- Azure estate and deployment boundaries
- Existing resources and resource ownership
- Network and DNS architecture
- Identity and access requirements
- Security and compliance constraints
- Governance and FinOps requirements
- Reliability and operational requirements
- Monitoring and observability requirements
- CI/CD and validation requirements
- Prohibited changes
- Dependencies
- Confirmed decisions
- Explicit assumptions
- Open questions
- Readiness for specification

## Non-Negotiable Rules

1. Ask questions before making architecture decisions.
2. Never invent tenant IDs, subscription IDs, resource IDs, IP ranges, resource
   names, owners, policies, environments, regions, SKUs, or compliance
   requirements.
3. Never convert an assumption into a confirmed fact.
4. Clearly distinguish facts, requirements, constraints, decisions, assumptions,
   recommendations, and open questions.
5. Do not generate Bicep, Terraform, deployment scripts, application code, or
   pipeline code during the interview.
6. Do not create or modify Azure resources.
7. Do not execute deployments, What-If operations, or write operations against
   Azure.
8. Do not request, display, or store passwords, client secrets, access keys,
   certificates, tokens, or other secret values.
9. Resource IDs and object IDs are identifiers and may be captured when needed.
10. Treat repository inspection and Azure discovery as read-only activities.
11. Obtain explicit user approval before running any read-only Azure discovery
    command.
12. Record unknown information as unknown; do not fill gaps with likely values.
13. Ask only questions relevant to the current solution.
14. Explain unfamiliar Azure terminology briefly when the user needs to make a
    decision.
15. Do not ask the user to repeat information already provided or reliably found
    in approved source material.
16. Prefer stable identifiers such as Azure resource IDs over display names.
17. Existing resources must be classified individually as discover, reuse,
    create, migrate, or replace.
18. Record whether each existing resource may be modified by the future
    deployment.
19. A recommendation is not a decision until the user confirms it.
20. The interview may only be declared ready when the readiness gate passes.

## Prerequisites

Before starting:

1. Confirm that the current directory is a Spec Kit project.
2. Confirm that `.specify/` exists.
3. Locate the installed extension templates under the extension installation.
4. Read `.specify/memory/constitution.md` when it exists.
5. Inspect existing interview artifacts when they exist.
6. Do not require a completed constitution to start the interview.
7. If the current directory is not a Spec Kit project, stop and instruct the
   user to initialize it with `specify init`.

## Artifact Locations

Use these project-local artifacts:

```text
.specify/discovery/azure-context.md
.specify/discovery/azure-context.json
```

Create and continuously maintain `azure-context.md` from the beginning of the
interview.

Create `azure-context.json` only when all schema-required fields have confirmed
or explicitly accepted values and the document can pass schema validation.
Never populate required JSON properties with invented values or placeholders
merely to create the file early.

Use these installed extension resources as the source templates:

```text
.specify/extensions/azure-interview/templates/azure-context-template.md
.specify/extensions/azure-interview/templates/azure-context.schema.json
```

If the exact installation location differs, locate the installed
`azure-interview` extension without modifying it.

The artifacts have separate lifecycle responsibilities:

- `azure-context.md` is the continuously updated human-readable interview record.
- `azure-context.json` is the validated machine-readable handoff contract.
- Markdown may contain incomplete sections and explicit placeholders during the
  interview.
- JSON must never contain placeholder values solely to satisfy the schema.

Create `.specify/discovery/` when it does not exist.

## Resume Behaviour

If either output artifact already exists:

1. Read all existing interview artifacts.
2. Summarize the current interview state.
3. Preserve confirmed answers and identifiers.
4. Continue with the earliest incomplete relevant topic.
5. Ask whether changed user input supersedes an earlier confirmed answer when a
   conflict is detected.
6. Never silently discard previous answers.
7. Update the last-updated timestamp while preserving the original creation
   timestamp.
8. Do not create duplicate decision, assumption, dependency, or question IDs.
9. If Markdown exists without JSON, treat that as a normal in-progress state.
10. If JSON exists, validate it before relying on it.
11. When Markdown and JSON conflict, stop handoff and reconcile the difference
    with the user.

## Interview Style

1. Ask exactly one primary question per response.
2. Never combine independent decisions in one question, questionnaire, form, or
   tool invocation.
3. A primary question may contain multiple fields only when they describe one
   inseparable fact, such as a resource name together with its resource ID.
4. Provide two to five mutually exclusive answer options when that improves
   clarity.
5. Put the recommended option first and explain why it is recommended.
6. Always permit a free-form answer.
7. Explain the consequence of each material choice.
8. Confirm a section before moving to the next major section.
9. Periodically summarize what has been confirmed and what remains open.
10. Avoid presenting the complete questionnaire at once.
11. Skip sections that are demonstrably irrelevant.
12. Reopen a skipped section when a later answer makes it relevant.
13. Challenge contradictions respectfully and request a decision.
14. Do not declare an answer confirmed until the user has answered or approved
    the proposed interpretation.
15. When the user says `GROEN`, treat the immediately preceding summary, answer,
    or proposed interpretation as confirmed and continue to the next unresolved
    item.
16. `GROEN` does not approve Azure commands, deployments, destructive actions,
    secrets handling, or unrelated changes.
17. End every response with exactly one next question or one explicit request
    for confirmation.
18. Do not advance to a later interview phase while an earlier blocking question
    remains unresolved.

## Evidence Classification

Every material statement must be traceable to one of these sources:

| Source | Meaning |
|---|---|
| `user` | Explicitly stated or confirmed by the user |
| `repository` | Found in project files |
| `azure` | Found through an approved read-only Azure query |
| `documentation` | Found in supplied or authoritative documentation |
| `policy` | Derived from an identified organizational policy |

Classify information as:

| Type | Meaning |
|---|---|
| Fact | Verifiable current-state information |
| Requirement | Something the solution must achieve |
| Constraint | A boundary the solution must respect |
| Decision | A choice confirmed by an authorized person |
| Assumption | An unverified statement temporarily used for progress |
| Recommendation | Advice awaiting confirmation |
| Open question | Information or a decision still required |

Never use `recommendation` and `decision` interchangeably.

## Adaptive Interview Flow

Execute the phases in order, but ask only applicable questions.

### Phase 0: Initialize

Determine:

- Whether this is a new or resumed interview
- The initial workload description
- Whether relevant repository documentation is available
- Whether the user wants repository inspection
- Whether a constitution exists
- Which information is already known
- Who is authorized to confirm the interview

Create the draft Markdown artifact as soon as enough information exists to
identify the workload. Set its interview status to `In Progress` and readiness
to `No`.

Do not create the JSON artifact during initialization unless every required
schema property can be populated from confirmed information. Missing JSON at
this stage is expected and is not an interview failure.

If the initial workload description is vague, the first interview question must
ask only which specific business capability or problem the workload addresses.

Do not combine that first question with requests for the workload name, owners,
users, lifecycle, environments, criticality, architecture, AVM strategy,
subscriptions, resource names, or any other independent fact.

Record the answer first. Ask for the workload name only in the next response
when it was not already provided by the user.

### Phase 1: Workload and Outcome

Complete Phase 1 in this strict order:

1. Establish the specific business capability or problem.
2. Identify intended users or consumers.
3. Confirm the required business outcome and measurable success.
4. Confirm lifecycle and target environments.
5. Confirm in-scope and out-of-scope boundaries.
6. Only then ask about production criticality and delivery constraints.

Do not ask about criticality, topology, AVM strategy, subscriptions, or
implementation choices before the business capability has been clearly
described. If the business purpose is still vague, the next question must
clarify that purpose.

Discover:

- Workload name
- Business purpose
- Business owner
- Technical owner
- Intended users or consumers
- Required business outcome
- Greenfield, brownfield, migration, or extension lifecycle
- Target environments
- Production criticality
- Delivery constraints
- In-scope capabilities
- Out-of-scope capabilities
- Measurable success criteria

Do not accept “deploy Azure resources” as the complete business purpose. Ask
what capability those resources must enable.

Do not infer mission criticality merely because the workload will run in
production.

### Phase 2: Azure Estate and Boundaries

Discover:

- Microsoft Entra tenant
- Management-group placement
- Subscription per environment
- Resource-group strategy
- Primary and secondary regions
- Data-residency requirements
- Existing landing-zone presence
- Platform-team responsibilities
- Workload-team responsibilities
- Deployment scope
- Cross-subscription dependencies
- Cross-tenant dependencies

Ask for IDs only when known and relevant. Do not block early discovery merely
because exact IDs are not yet available. Track missing required IDs explicitly.

Never infer that all environments share a subscription, region, management
group, or resource-group strategy.

### Phase 3: Existing Resources

First determine whether the solution:

- Creates an entirely new environment
- Reuses existing platform services
- Extends an existing workload
- Migrates existing resources
- Replaces existing resources
- Requires discovery before this is known

For every relevant resource capture:

- Azure resource type
- Resource name
- Full resource ID when available
- Environment
- Owner
- Lifecycle intent: discover, reuse, create, migrate, or replace
- Whether the future deployment may modify it
- Required integrations
- Resource-lock implications
- Deletion or replacement prohibition
- Source of the information

Pay particular attention to existing:

- Virtual networks and subnets
- Azure Firewall and firewall policies
- Route tables
- Network security groups
- Private DNS zones
- Private DNS Resolver
- Log Analytics workspaces
- Action groups
- Key Vaults
- Managed identities
- Container registries
- Storage accounts
- App Service plans
- Front Door profiles
- API Management instances
- Databases
- Backup vaults
- Azure DevOps service connections

Do not assume that reusing a resource authorizes modifying it.

Do not classify a resource as `create` merely because its resource ID is not
known. Determine lifecycle intent independently from identifier availability.

### Phase 4: Network Topology

Determine the topology before asking hub-specific questions:

- Standalone network
- Existing hub-and-spoke
- New hub-and-spoke
- Azure Virtual WAN
- Platform landing-zone pattern
- No workload virtual network
- Other
- Undetermined

When hub-and-spoke applies, discover:

- Existing or new hub
- Hub name and resource ID
- Hub subscription and resource group
- Hub owner
- Existing or new spoke
- Spoke name and resource ID
- Address spaces
- Subnet purposes and prefixes
- Peering ownership
- Peering configuration constraints
- Central or local ingress
- Central or local egress
- Azure Firewall routing
- Route tables and propagated routes
- Network security groups
- DDoS protection requirements
- Service endpoints
- Private endpoints
- On-premises connectivity
- VPN and ExpressRoute dependencies
- IP overlap validation
- Network-management boundaries

If IP ranges are unknown, record IP allocation as a blocking dependency owned by
the appropriate team. Never propose an arbitrary production address space as a
confirmed value.

If a workload does not require a virtual network, record that decision and skip
irrelevant subnet, peering, and routing questions.

### Phase 5: Private Connectivity and DNS

When private endpoints, private services, or hybrid name resolution apply,
discover:

- Services requiring private endpoints
- Whether public network access must be disabled
- Private endpoint subnet and ownership
- Private DNS zone location
- Private DNS zone subscription and resource group
- Existing zone resource IDs
- Zone ownership
- VNet-link ownership
- Whether the workload deployment may create zone groups
- Whether the workload deployment may create VNet links
- Azure Private DNS Resolver presence
- Inbound and outbound endpoint dependencies
- On-premises conditional forwarding
- Split-horizon DNS requirements
- Custom DNS servers
- DNS record ownership
- DNS changes prohibited to the workload deployment

Distinguish among:

- Creating a Private DNS zone
- Reusing an existing Private DNS zone
- Linking a virtual network to a zone
- Associating a private endpoint through a zone group
- Creating DNS records
- Forwarding DNS queries

These are separate permissions and lifecycle decisions.

Do not infer that Private DNS zones belong in the hub merely because a
hub-and-spoke topology exists.

### Phase 6: Identity and Access

Discover:

- Deployment identity
- Workload identities
- System-assigned or user-assigned managed identities
- Microsoft Entra groups
- Administrative Units
- RBAC model
- Required roles
- Role-assignment scopes
- Role-assignment owner
- Privileged Identity Management requirements
- Cross-tenant authentication
- Federated workload identity
- Secretless deployment expectations
- Break-glass or emergency-access requirements

Never request credential values. Record only the intended secret source or
identity mechanism.

Distinguish deployment identity, runtime workload identity, administrator
identity, and end-user authentication.

### Phase 7: Security and Compliance

Discover:

- Applicable compliance frameworks
- Organizational security baseline
- Azure Policy assignments and initiatives
- Public exposure permitted or prohibited
- Network-isolation requirements
- Encryption requirements
- Customer-managed key requirements
- Key Vault strategy
- Secret-management requirements
- Certificate-management requirements
- Defender for Cloud requirements
- Resource locks
- Data classification
- Data retention
- Logging and audit requirements
- Vulnerability-scanning requirements
- Required security approvals
- Explicit exceptions and their approvers

When an existing Key Vault is used, capture:

- Resource ID
- Owner
- RBAC or access-policy model
- Whether role assignments may be created
- Whether secrets, keys, or certificates may be created
- Whether networking may be modified
- Private endpoint and DNS ownership
- Diagnostic-setting ownership
- Resource-lock restrictions

Do not assume customer-managed keys are required solely because the workload is
production or security-sensitive.

### Phase 8: Governance and FinOps

Discover:

- Naming convention
- Required tags
- Tag values per environment
- Resource ownership
- Cost center
- Budget constraints
- Budget alerts
- Allowed regions
- Allowed SKUs
- Denied SKUs or resource types
- Reservation or savings-plan considerations
- Scaling constraints
- Cost-estimation requirements
- Azure Policy exception process
- Resource lifecycle and decommissioning requirements

Separate organizational rules, which may belong in the constitution, from
workload-specific requirements, which belong in the interview.

Do not copy organization-wide rules into the interview as confirmed requirements
unless their applicability to this workload is established.

### Phase 9: Reliability and Operations

Discover:

- Availability target
- High-availability requirements
- Zone-redundancy requirements
- Disaster-recovery requirements
- Recovery Time Objective
- Recovery Point Objective
- Backup requirements
- Restore-testing requirements
- Maintenance windows
- Patch-management requirements
- Scaling requirements
- Capacity expectations
- Operational support team
- Incident-management integration
- Runbook requirements
- Service-health requirements
- Dependency failure behaviour

Do not automatically prescribe high availability or disaster recovery. Tie each
recommendation to the confirmed business criticality and recovery requirements.

Treat availability, backup, and disaster recovery as separate concerns.

### Phase 10: Monitoring and Observability

Discover:

- Existing or new Log Analytics workspace
- Workspace resource ID and owner
- Diagnostic-setting ownership
- Required logs and metrics
- Retention requirements
- Alert rules
- Action groups
- Notification recipients by role or team
- Dashboard requirements
- Application Insights requirements
- Microsoft Sentinel integration
- Datadog, Grafana, or other external integrations
- Audit-evidence requirements
- Cost constraints for logging

Do not assume that use of a central workspace grants permission to create or
modify diagnostic settings, alerts, action groups, or retention settings.

### Phase 11: Delivery and Validation

Discover:

- Infrastructure-as-Code language
- AVM-only, AVM-preferred, or other module strategy
- Repository and folder structure
- CI/CD platform
- Branching strategy
- Deployment identity or service connection
- Federated identity requirements
- Deployment scope
- Parameter-management strategy
- Environment-specific configuration
- Secret-injection strategy
- Approval gates
- Separation of duties
- Validation commands
- Linting requirements
- Security scanning
- Policy validation
- PSRule for Azure
- What-If requirements
- Test deployment requirements
- Rollback or forward-fix strategy
- Evidence and documentation requirements

Do not create the implementation plan during this phase. Capture constraints and
expected validation outcomes only.

Do not ask the user to choose AVM-only or AVM-preferred until the business scope,
existing-resource context, and applicable constitution constraints are known.

### Phase 12: Prohibited Changes and Ownership

Ask explicitly:

- Which existing resources must never be modified?
- Which resources may be referenced but not managed?
- Which resources are owned by another team?
- Which deployment scopes are prohibited?
- May role assignments be created?
- May diagnostic settings be changed?
- May network peerings, routes, firewall policies, DNS zones, links, records, or
  private endpoint zone groups be changed?
- May locks be added, changed, or removed?
- May existing resources be imported into IaC management?
- What requires separate approval?

Record prohibited changes as direct, testable statements.

A missing permission must not be interpreted as permission granted.

### Phase 13: Review and Reconciliation

Before readiness assessment:

1. Present a concise summary grouped by major section.
2. List all existing resources and their lifecycle intent.
3. List all prohibited changes.
4. List confirmed decisions.
5. List assumptions.
6. List dependencies.
7. List open questions.
8. Identify contradictions.
9. Identify missing identifiers.
10. Ask the user to correct or confirm the summary.
11. Update the Markdown artifact after confirmation.
12. Generate or update the JSON artifact only when it can satisfy the schema.
13. Validate the JSON artifact before declaring readiness.

When repository or Azure evidence conflicts with user input, present both
sources and ask the user which statement is authoritative. Preserve the conflict
until resolved.

## Read-Only Repository Inspection

Repository inspection may be performed when:

- The user supplied repository content as interview input.
- The current project contains relevant infrastructure or documentation.
- Inspection stays within the current project or an explicitly approved path.

Before relying on repository evidence:

1. Identify the inspected file.
2. Distinguish explicit configuration from inferred architecture.
3. Record the source as `repository`.
4. Ask the user to confirm material interpretations.
5. Do not treat examples, generated output, test fixtures, or commented code as
   active production configuration without confirmation.

## Read-Only Azure Discovery

Azure discovery is optional and never implied by invoking this command.

Before running any Azure command:

1. Explain which read-only command is proposed.
2. Explain what information it will retrieve.
3. Confirm the tenant and subscription context.
4. Obtain explicit user approval.
5. Use only read operations.
6. Avoid commands that expose secret values.
7. Record retrieved evidence with source `azure`.
8. Ask the user to confirm architectural interpretations.

Examples of potentially acceptable read-only operations include listing resource
metadata, retrieving resource IDs, inspecting network topology, and checking
policy assignments.

The following are prohibited during the interview:

- Deployments
- What-If execution
- Resource creation
- Resource updates
- Resource deletion
- Role-assignment changes
- Policy changes
- Secret retrieval
- Key retrieval
- Certificate retrieval
- Credential generation
- Access-token output

## Readiness Gate

Set `readyForSpecification` to `true` only when all the following are true:

1. The workload purpose is confirmed.
2. Intended users or consumers are identified.
3. Required outcomes and measurable success are confirmed.
4. In-scope and out-of-scope boundaries are confirmed.
5. Target environments are known.
6. Deployment lifecycle is known.
7. Azure deployment boundaries are sufficiently identified.
8. Applicable network topology is known.
9. Existing resources have lifecycle intent and ownership.
10. Required existing resource IDs are present or explicitly not required.
11. Modification permissions for reused resources are known.
12. Security and compliance constraints are confirmed.
13. Identity and RBAC responsibilities are known.
14. Private endpoint and DNS ownership are known when applicable.
15. Operational and observability expectations are known.
16. Delivery and validation requirements are known.
17. Prohibited changes are recorded.
18. No blocking open questions remain.
19. No critical assumption remains unvalidated.
20. No material contradiction remains unresolved.
21. The user has confirmed the final interview summary.
22. The JSON artifact exists and passes schema validation.

A non-blocking question may remain only when:

- It does not change solution scope or architecture.
- It does not affect security, compliance, identity, networking, DNS, data
  protection, resource ownership, or deployment safety.
- Its owner and resolution point are recorded.
- The user explicitly accepts deferring it.

If the gate fails:

- Set interview status to `Blocked` or `In Progress`.
- Set readiness to `No`.
- Explain exactly what prevents handoff.
- Continue with the earliest and highest-impact missing question.
- Do not generate a handoff instruction.

If the gate passes:

- Generate the machine-readable JSON artifact.
- Validate the JSON artifact.
- Set interview status to `Complete`.
- Set `readyForSpecification` to `true`.
- Set all readiness counters to zero.
- Ask the user for final confirmation before producing the handoff.

## JSON Generation Requirements

Generate `azure-context.json` only after sufficient confirmed information exists
to populate every required schema property without invented values or
placeholders.

The JSON artifact must validate against:

```text
.specify/extensions/azure-interview/templates/azure-context.schema.json
```

Requirements:

1. Emit valid UTF-8 JSON without comments.
2. Use ISO 8601 UTC timestamps.
3. Use exact enum values defined by the schema.
4. Use empty arrays only when the corresponding topic was considered and has no
   applicable entries.
5. Do not use placeholder values such as `TBD`, `unknown`, `example`, or
   `to-be-confirmed` unless the schema explicitly defines that value and the user
   confirmed it.
6. Use `null` only where the schema permits it.
7. Keep identifiers stable across resumed sessions.
8. Keep Markdown and JSON semantically synchronized.
9. Do not mark the interview complete when schema validation fails.
10. Report validation errors without discarding valid interview data.
11. If the validator cannot run, keep readiness set to `No` and report the
    validator dependency as the blocking issue.
12. Never weaken or modify the schema from within a consuming project.

When available, validate with:

```text
python .specify/extensions/azure-interview/scripts/python/validate_context.py \
  .specify/discovery/azure-context.json \
  --schema .specify/extensions/azure-interview/templates/azure-context.schema.json
```

On PowerShell, the equivalent is:

```powershell
python .\.specify\extensions\azure-interview\scripts\python\validate_context.py `
  .\.specify\discovery\azure-context.json `
  --schema .\.specify\extensions\azure-interview\templates\azure-context.schema.json
```

Do not install Python packages without user approval. If the `jsonschema`
dependency is unavailable, explain how the user can install the extension's
runtime requirements:

```powershell
python -m pip install -r `
  .\.specify\extensions\azure-interview\requirements-runtime.txt
```

## Identifier Rules

Use stable sequential identifiers:

```text
DEP-001  Dependency
DEC-001  Decision
ASM-001  Assumption
OQ-001   Open question
```

Never reuse an identifier for a different item.

When an item is superseded, retain it with its updated status rather than
silently deleting its history from an active interview.

When an open question is answered:

1. Update its status.
2. Record the confirmed answer in the appropriate section.
3. Create a decision entry only when an actual choice was made.
4. Do not create a decision entry for every factual answer.

## Markdown Quality Rules

When updating `azure-context.md`:

1. Preserve the template section order.
2. Use `TBD` only for genuinely incomplete draft fields.
3. Remove obsolete `TBD` rows when confirmed entries exist.
4. Keep table columns structurally valid.
5. Keep each tracked item on one logical table row.
6. Do not split a table row across multiple lines.
7. Use `Yes`, `No`, `Unknown`, or `Not applicable` consistently where relevant.
8. Do not describe unconfirmed suggestions as confirmed decisions.
9. Update readiness counts after each answer.
10. Keep the current blocking question synchronized with the next question asked.
11. Avoid duplicate entries across decisions, assumptions, and open questions.
12. Preserve user-confirmed wording for prohibitions and ownership boundaries.

## Specification Handoff

After the readiness gate passes, provide this next-step instruction:

```text
Run /speckit.specify and instruct it to use
.specify/discovery/azure-context.md and
.specify/discovery/azure-context.json as authoritative discovery input.

Preserve confirmed requirements, constraints, existing-resource lifecycle
intent, ownership boundaries, and prohibited changes. Do not treat assumptions
as facts. Do not invent missing Azure details.
```

Adapt the visible invocation syntax to the active integration when necessary,
but do not alter the meaning of the core Spec Kit command.

Do not automatically execute `/speckit.specify`. The user remains in control of
starting the core Spec Kit workflow.

## Completion Response

At the end of each invocation, report:

- Interview status
- Current phase
- Sections completed
- Current blocking item
- Number of blocking questions
- Number of critical unvalidated assumptions
- Markdown artifact path
- JSON artifact path or `Not created yet`
- Whether the interview is ready for specification
- Exactly one next question or confirmation request

Keep the response concise.

During an incomplete interview, do not provide multiple unrelated questions,
implementation recommendations, or a specification handoff.