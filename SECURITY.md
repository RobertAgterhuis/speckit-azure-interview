# Security Policy

## Supported Versions

Security fixes are provided for the latest released version.

| Version | Supported |
|---|---:|
| Latest release | Yes |
| Earlier releases | No |
| Unreleased development branch | Best effort |

## Reporting a Vulnerability

Do not report a suspected vulnerability through a public GitHub issue.

Use GitHub Private Vulnerability Reporting when it is enabled for this
repository:

1. Open the repository on GitHub.
2. Select **Security**.
3. Select **Advisories**.
4. Select **Report a vulnerability**.
5. Include the affected version, reproduction steps, impact, and any suggested
   remediation.

If Private Vulnerability Reporting is unavailable, contact the repository owner
privately before publishing details.

Do not include:

- Passwords
- Access tokens
- Client secrets
- Certificates or private keys
- Azure access keys
- Production resource data
- Personally identifiable information

## Expected Response

The project owner will aim to:

- Acknowledge the report within five business days.
- Confirm whether the issue can be reproduced.
- Assess severity and affected versions.
- Coordinate remediation and disclosure.
- Credit the reporter when requested and appropriate.

These targets are best-effort commitments for an open-source project.

## Security Scope

Security reports may include:

- Path traversal
- Unsafe file replacement
- Secret disclosure
- Unexpected Azure write operations
- Command or prompt injection
- Bypass of the specification-readiness gate
- Incorrect classification of untrusted evidence as confirmed fact
- Installation outside the intended extension or Hermes skill roots
- Unsafe handling of existing Azure resources
- Dependency vulnerabilities
- Supply-chain concerns

## Trust Model

Spec Kit extensions run with the privileges of the active AI agent. Users must
review extensions before installation.

This extension is designed to:

- Perform discovery rather than implementation.
- Avoid Azure write operations.
- Require explicit approval before read-only Azure discovery.
- Avoid requesting or storing secret values.
- Validate calculated file paths.
- Refuse silent replacement of differing Hermes skill content.
- Create a backup before an approved forced replacement.
- Keep incomplete interviews blocked from specification handoff.
- Separate assumptions from confirmed facts.

## Azure Safety Boundary

The interview command must not:

- Create, update, or delete Azure resources.
- Run deployments.
- Run Azure What-If operations.
- Change role assignments.
- Change Azure Policy.
- Retrieve secret, key, or certificate values.
- Output access tokens.
- Generate credentials.

A violation of this boundary should be treated as a security issue.

## Dependency Security

Runtime dependencies are intentionally minimal and listed in
`requirements-runtime.txt`.

Development dependencies are listed separately in `requirements-dev.txt`.

Dependency updates must:

- Remain within reviewed major-version ranges.
- Pass all automated tests.
- Avoid adding unnecessary runtime packages.
- Be reviewed for licensing and supply-chain risk.

## Coordinated Disclosure

Please allow reasonable time for investigation and remediation before public
disclosure. The project owner will communicate status and expected resolution
when the report is confirmed.