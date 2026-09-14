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

[Unreleased]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/releases/tag/v0.1.0