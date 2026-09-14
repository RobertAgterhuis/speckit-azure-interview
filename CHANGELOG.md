# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Optional read-only Azure inventory discovery.
- Additional brownfield validation.
- Azure Verified Modules recommendation support.
- Azure Well-Architected Framework review support.
- Cloud Adoption Framework review support.
- Azure DevOps pipeline requirement validation.
- Additional integration tests for supported AI platforms.

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

[Unreleased]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/RobertAgterhuis/speckit-azure-interview/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/RobertAgterhuis/speckit-azure-interview/releases/tag/v0.1.0