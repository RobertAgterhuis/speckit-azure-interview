---
title: "Design Review Evidence"
description: "Understand the review record, digest binding, and implementation authorization."
---

Design Review Evidence records an explicit human approval or rejection of one
exact intended-state Azure architecture.

It does not represent deployed or observed Azure state.

## Artifacts

The review creates two evidence files:

| Artifact | Purpose |
| --- | --- |
| `.specify/design/azure-design-review.json` | Machine-readable terminal decision |
| `.specify/design/azure-design-review.md` | Human-readable review summary |

The same transaction updates:

- `.specify/design/azure-design-model.json`;
- `.specify/design/azure-design-overview.md`;
- `.specify/design/azure-design-overview.svg`;
- `.specify/design/azure-design-overview.drawio`.

All six files must represent the same review status.

## Review record

The JSON record contains:

- `schemaVersion`;
- `reviewStatus`;
- the canonical `designModel` path;
- `designDigest`;
- `reviewedBy`;
- `reviewedAt`;
- optional `comment`;
- `findings`;
- `implementationAuthorized`.

Unknown properties are rejected by
`azure-design-review.schema.json`.

## Decision invariants

An approved review requires:

```text
reviewStatus: approved
findings: []
implementationAuthorized: true
```

A rejected review requires:

```text
reviewStatus: rejected
findings: at least one actionable item
implementationAuthorized: false
```

Conditional approval is not supported.

## SHA-256 binding

The review includes a lowercase SHA-256 digest of the final reviewed
`azure-design-model.json`.

```json
{
  "designDigest": {
    "algorithm": "sha256",
    "value": "<64 lowercase hexadecimal characters>"
  }
}
```

This digest binds the human decision to exact design content. Modifying the
design after review invalidates the recorded relationship and requires another
review.

## Transactional publication

Before replacing any artifact, the review implementation:

1. validates paths and schemas;
2. applies the terminal decision;
3. renders every synchronized representation;
4. verifies the design digest;
5. validates SVG and Draw.io XML;
6. stages the complete artifact set.

If publication fails, previously replaced artifacts are restored. The operation
must not intentionally leave a mixed review state.

## Overwrite protection

Existing terminal review artifacts are protected.

Use `--overwrite` only after explicit human authorization to replace the
existing synchronized review record.

## Security boundary

`implementationAuthorized: true` authorizes progression within the documented
Spec Kit workflow. It does not:

- assign Azure RBAC;
- provide deployment credentials;
- execute infrastructure changes;
- prove that the intended design was deployed;
- verify runtime configuration.

As-built verification remains a separate lifecycle stage.
