# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Additional brownfield topology discovery.
- Azure Verified Modules recommendation support.
- Azure Well-Architected Framework review support.
- Cloud Adoption Framework review support.
- Azure DevOps pipeline requirement validation.
- Additional integration tests for supported AI platforms.

## [0.8.0] - 2026-09-15

### Added

- Brownfield topology discovery with six controlled topology relationship types:
  virtual-network subnet containment, virtual-network peering, subnet network
  security group and route-table associations, private-endpoint subnet
  placement, and Private DNS zone virtual-network links.
- Optional schema-validated `topology` evidence with deterministic relationship
  ordering, deduplication, endpoint types, counts, and target-scope
  classification.
- `in-scope`, `external-subscription`, and `unresolved` target classifications.
- Six-query provenance through `source.topologyQueries`.
- Pagination integrity checks for stable total-record counts, complete result
  collection, and non-repeating continuation tokens.
- Public operator, command, testing, Quick Start, and Starlight documentation
  for topology evidence and its limitations.

### Changed

- Azure inventory collection now uses seven separate Resource Graph query flows:
  one resource query and six controlled topology queries.
- Windows-safe KQL normalization converts controlled multiline queries into one
  command-line argument before execution through `az.cmd`.
- Inventory collection validates all query results before atomic artifact
  publication.
- Active immutable installation examples and package metadata now reference
  v0.8.0.

### Security

- Collection remains read-only and restricted to the explicitly approved tenant
  and subscription.
- External subscriptions are referenced but never queried.
- Only controlled relationship projections enter the evidence document.
- Query, pagination, schema, or semantic failures cannot publish partial
  inventory evidence or replace existing evidence.
- Discovered topology remains `unconfirmed` and grants no permission to reuse,
  modify, move, replace, or delete Azure resources.

## [0.7.0] - 2026-09-15

### Added

- Adaptive numbered interview batches containing two to four closely related,
  independent questions.
- Deterministic batch planning based on phase, topic cluster, dependencies,
  prior answers, repository evidence, and confirmed inventory evidence.
- Explicit question clusters for workload foundation, Azure placement,
  existing-resource boundaries, networking, governance, and operations.
- Support for partial batch responses and explicit `unknown`, `TBD`,
  `not applicable`, and `use existing` answers.
- Scope-wide answer generalization with explicit exception handling.
- A synchronized completion transaction for final Markdown and JSON artifacts.
- Rollback and post-publication validation requirements for interview handoff
  artifacts.
- Public documentation and examples for answering adaptive question batches.

### Changed

- The first business-purpose question remains isolated, while later independent
  questions can be asked efficiently in related batches.
- Interview phases now recompute applicable questions after every response
  instead of following a fixed questionnaire.
- Existing-resource and inventory reconciliation can confirm scoped evidence in
  bulk without inferring modification permission.
- Protected decisions remain isolated from ordinary adaptive batches.
- Final handoff instructions are provided only after persisted Markdown and JSON
  both pass completion and readiness verification.
- Updated active installation examples and package metadata to v0.7.0.

### Security

- Approval, consent, security exceptions, destructive actions, overwrite
  permission, and modification permission remain individually attributable
  protected decisions.
- Repository and inventory evidence can propose answers but cannot silently
  confirm human decisions.
- Failed candidate validation cannot publish a partially complete handoff.
- Failed artifact replacement requires restoration of previously replaced
  interview artifacts.
- Downstream commands cannot construct or repair an incomplete interview
  context.

## [0.6.0] - 2026-09-15

### Added

- `speckit.azure-interview.design-review` explicit intended-design review
  command.
- `scripts/python/review_azure_design.py` executable review workflow.
- `templates/azure-design-review.schema.json` terminal review contract.
- Machine-readable `.specify/design/azure-design-review.json` evidence.
- Human-readable `.specify/design/azure-design-review.md` summary.
- Explicit `approved` and `rejected` decision invariants.
- Named human reviewer and UTC review timestamp requirements.
- Lowercase SHA-256 digest binding to the final reviewed design model.
- `implementationAuthorized` workflow-control value.
- Rejection findings with actionable validation.
- Synchronized review status in Markdown, SVG, and Draw.io artifacts.
- Transactional six-artifact publication with rollback behavior.
- Dedicated Azure Intended Design Review operator guide.
- Starlight command and design-review evidence pages.
- Comprehensive schema, semantic, rendering, transaction, and CLI tests.

### Changed

- Updated the extension and documentation package versions to `0.6.0`.
- Registered the review command, schema, and executable in `extension.yml`.
- Extended the documented lifecycle with a Design Review Decision before
  Specify.
- Updated active installation examples to the immutable v0.6.0 archive.
- Made SVG and Draw.io review-status rendering dynamic.
- Updated Draw.io tests to identify architecture nodes through stable
  `data-node-id` attributes.
- Extended README, Quick Start, architecture, testing, Codex, Copilot, and
  Starlight documentation.

### Fixed

- Added a narrow Git ignore exception so Starlight artifact documentation is
  included in source control and GitHub Pages builds.

### Security

- Approval requires an explicit attributable human decision.
- Approval cannot contain unresolved findings.
- Rejection requires at least one actionable finding.
- Existing terminal reviews cannot be replaced without `--overwrite`.
- Review inputs and outputs remain constrained to `.specify/design`.
- Review records are cryptographically bound to exact design content.
- Publication failures restore previously replaced artifacts.
- Review generation performs no Azure write operations and does not prove
  deployed Azure state.

## [0.5.0] - 2026-09-14

### Added

- `speckit.azure-interview.design` intended-architecture command.
- Validated `.specify/design/azure-design-model.json` design contract.
- Human-reviewable `.specify/design/azure-design-overview.md` artifact.
- Deterministic Mermaid intended-architecture diagram.
- Standalone `.specify/design/azure-design-overview.svg` diagram.
- Editable `.specify/design/azure-design-overview.drawio` diagram.
- Existing-versus-planned resource visualization.
- Architecture relationships for hub peering, subnets, central egress,
  private DNS, private endpoints, and diagnostic settings.
- Stable node and relationship identifiers.
- JSON Schema and semantic validation for intended-design models.
- Explicit overwrite protection across the complete design artifact set.
- Safe escaping for Markdown, Mermaid, SVG, XML, and Draw.io content.
- Comprehensive generator, schema, rendering, command, and package tests.

### Changed

- Updated the extension manifest to version `0.5.0`.
- Registered the design command, generator, and schema as packaged resources.
- Updated active installation examples to the immutable v0.5.0 archive.
- Extended the post-interview workflow with an explicit human design-review
  stage before implementation.

### Security

- Intended designs remain `unreviewed` until explicit human approval.
- Design generation cannot claim or prove deployed Azure state.
- Existing output artifacts cannot be replaced without `--overwrite`.
- Input and output paths remain constrained to the consumer Spec Kit project.
- Relationship endpoints must reference valid architecture nodes.

## [0.4.0] - 2026-09-14

### Added

- Optional, subscription-scoped Azure Inventory Discovery command.
- Read-only Azure CLI and Azure Resource Graph inventory collector.
- Explicit tenant and subscription UUID validation.
- Mandatory `--approve-read-only` execution consent.
- Optional tenant-context enforcement.
- Project-local `.specify/discovery/azure-inventory.json` evidence artifact.
- JSON Schema for Azure inventory evidence.
- Semantic validation for inventory resource counts.
- Local eight-field resource metadata allowlist.
- Windows `az.cmd` launcher fallback while retaining `shell=False`.
- Atomic evidence-file publication.
- Explicit `--overwrite` behavior for refreshing existing evidence.
- Dedicated Azure Inventory operator documentation.
- Interview reconciliation rules for unconfirmed Azure evidence.
- Comprehensive collector, schema, command, and documentation tests.

### Changed

- Updated the extension manifest to version `0.4.0`.
- Added `speckit.azure-interview.inventory` to the extension manifest.
- Added the inventory schema and collector to packaged extension resources.
- Updated README, Quick Start, architecture, testing, Codex, and Copilot
  documentation for the v0.4.0 release.
- Updated public installation examples to the immutable v0.4.0 archive.
- Minimized `az account show` output to tenant ID, subscription ID,
  subscription name, and state.
- The main interview now detects and reconciles optional inventory evidence.

### Security

- Azure commands execute through argument arrays with `shell=False`.
- Inventory is limited to one explicitly approved subscription.
- Cross-subscription resource records are rejected.
- Unexpected properties, identities, tags, SKUs, plans, zones, extended
  locations, and other fields are removed before persistence.
- Existing output is rejected before Azure is contacted unless overwrite was
  explicitly approved.
- Inventory evidence remains `unconfirmed` and is never merged automatically
  into the confirmed interview context.
- The collector performs no deployments, What-If operations, resource changes,
  role-assignment changes, policy changes, or secret retrieval.

### Verified

- Live Windows smoke test completed against one approved sandbox subscription.
- The collector validated the active tenant and subscription.
- Windows safely retried the `az.cmd` launcher without enabling a shell.
- Azure Resource Graph returned seven resources.
- The local metadata allowlist retained only the eight approved fields.
- The output schema and semantic checks passed before artifact creation.
- The artifact recorded `readOnly: true` and
  `evidenceStatus: unconfirmed`.
- The focused Azure inventory suite passed 68 tests.
- The complete repository suite passed 107 tests before final release updates.

### Known Limitations

- Baseline discovery collects resource metadata only; it does not yet interpret
  network topology, private DNS relationships, policy compliance, diagnostic
  settings, or resource configuration payloads.
- Resource ownership, purpose, environment, lifecycle intent, and modification
  permission still require human confirmation.
- Discovery is currently limited to one subscription per invocation.
- Azure CLI authentication and Azure Resource Graph access must already be
  available on the operator workstation.

## [0.2.0] - 2026-09-14

### Added

- Verified OpenAI Codex CLI integration through the Spec Kit
  `.agents/skills` convention.
- Dedicated Codex integration guide covering setup, skill invocation,
  filesystem approvals, readiness validation, and troubleshooting.
- Codex behavioral smoke-test procedure and acceptance criteria.
- Root-level Quick Start covering prerequisites, original GitHub Spec Kit
  installation, extension installation, integration-specific command notation,
  readiness validation, and the complete Constitution-to-Converge workflow.

### Changed

- Updated the supported-integration documentation to identify Codex as tested.
- Added Codex-specific `$speckit-*` invocation examples.
- Documented the difference between Codex, Claude, canonical-command, and
  Hermes invocation formats.
- Updated the extension manifest to version `0.2.0`.

### Verified

- Spec Kit initialized successfully with `--integration codex`.
- The extension generated
  `.agents/skills/speckit-azure-interview-run/SKILL.md`.
- Codex activated `$speckit-azure-interview-run`.
- Codex created the Markdown discovery artifact without premature JSON.
- Codex recorded only confirmed facts and preserved unknown values.
- Codex asked exactly one business-purpose question before architecture
  discovery.
- Codex did not generate IaC or perform Azure operations during the interview.
- Codex support was tested with Codex CLI `0.154.0` and Spec Kit CLI
  `1.0.7.dev0`.

## [0.1.1] - 2026-09-13

### Fixed

- Corrected the public installation instructions to use the supported
  `specify extension add <name> --from <archive-url>` syntax.
- Replaced the unsupported Git repository URL with an immutable versioned
  GitHub release archive.
- Documented the expected untrusted-source confirmation for extensions
  installed outside the official Spec Kit catalog.

## [0.1.0] - 2026-09-13

### Added

- Initial GitHub Spec Kit extension manifest.
- Namespaced `speckit.azure-interview.run` command.
- Provider-independent, adaptive Azure architecture interview workflow.
- Business-purpose-first interview safeguard.
- One-primary-question-per-response interview behavior.
- Greenfield, brownfield, migration, and extension classification.
- Existing-resource lifecycle and ownership capture.
- Hub-and-spoke and Virtual WAN discovery.
- Private endpoint and Private DNS discovery.
- Identity, security, governance, FinOps, and operations discovery.
- Delivery and validation requirement capture.
- Explicit prohibited-change registration.
- Human-readable Markdown discovery context template.
- Machine-readable JSON discovery context schema.
- Deferred JSON generation until all required values are confirmed.
- JSON Schema and semantic context validator.
- Stable validator exit codes for automation and CI use.
- Semantic validation for readiness counters, interview state, timestamps,
  blocking dependencies, duplicate identifiers, and reusable-resource IDs.
- Strict readiness gate before handoff to `/speckit.specify`.
- Representative valid brownfield hub-and-spoke context fixture.
- Automated validator and extension-package tests.
- Claude Code integration support.
- Hermes Agent compatibility adapter for custom `HERMES_HOME` installations.
- CI workflow for linting, formatting, YAML validation, and multi-platform tests.
- CodeQL security analysis workflow.
- Dependabot configuration for Python and GitHub Actions dependencies.
- Architecture, testing, Hermes integration, contribution, and security
  documentation.
- GitHub issue forms and pull-request template.

[Unreleased]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/releases/tag/v0.1.0