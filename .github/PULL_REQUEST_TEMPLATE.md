## Summary

Describe the problem and the outcome of this change.

## Change Type

- [ ] Interview behaviour
- [ ] JSON Schema or artifact contract
- [ ] Validator
- [ ] Hermes compatibility
- [ ] Documentation
- [ ] Tests or CI
- [ ] Dependency update
- [ ] Other

## Spec Kit Core Isolation

- [ ] This change does not modify or override a Spec Kit Core command.
- [ ] This change remains within the `azure-interview` extension namespace.
- [ ] This change does not require a fork of Spec Kit.

## Safety Review

- [ ] No Azure write operation was introduced.
- [ ] No deployment or What-If execution was introduced.
- [ ] No secret value is requested, stored, or displayed.
- [ ] Existing-resource ownership and modification permissions remain explicit.
- [ ] Assumptions cannot silently become confirmed facts.
- [ ] Path operations are validated and bounded.

## Interview Behaviour

- [ ] The interview asks exactly one primary question per response.
- [ ] Business purpose remains the first unresolved topic.
- [ ] Independent decisions are not combined.
- [ ] Incomplete interviews cannot pass the readiness gate.
- [ ] JSON is not generated with invented or placeholder values.
- [ ] Resume behaviour preserves confirmed information.

## Validation

- [ ] `python -m pytest -v` passes locally.
- [ ] The valid fixture passes direct schema validation.
- [ ] A clean extension development installation was tested.
- [ ] Generated installation content respects `.extensionignore`.

## Integration Smoke Tests

Indicate which integrations were tested:

- [ ] Claude Code
- [ ] Hermes
- [ ] Codex
- [ ] GitHub Copilot
- [ ] Other

Provide relevant results:

```text
Add concise smoke-test evidence here.
````

## Contract and Versioning

* [ ] No artifact-contract change
* [ ] Backward-compatible artifact-contract change
* [ ] Breaking artifact-contract change

Required version impact:

```text
None / Patch / Minor / Major
```

## Documentation

* [ ] README updated when required.
* [ ] CHANGELOG updated when required.
* [ ] Integration documentation updated when required.
* [ ] Migration guidance added for breaking changes.

## Additional Notes

Add decisions, limitations, follow-up work, or screenshots when relevant.

```
