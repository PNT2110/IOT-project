---
name: autonomous-research-fix-test
description: "Use when a repository task requires autonomous investigation, targeted research, implementation, regression fixing, and test validation. Trigger for requests to research a bug, find the root cause, implement a fix, run tests, or verify acceptance criteria in this workspace."
---

# Autonomous Research, Fix, Test

## Mission

Deliver a verified change, not only an explanation.

## Workflow

1. **Frame the task**
   - Extract requested behavior, constraints, acceptance criteria.
   - Identify affected package, contract, security boundary, and likely test surface.
   - Do not edit before understanding existing behavior.

2. **Inspect the repository**
   - Read `README.md`, relevant docs, contracts, implementation, tests, and repository guidance.
   - Search symbols, routes, configuration, error messages, and related tests.
   - Check current diagnostics and git diff before changes.

3. **Research only as needed**
   - Prefer repository evidence.
   - Use authoritative primary documentation for framework, protocol, security, or API behavior.
   - Record the relevant finding and version/date when external behavior matters.
   - Avoid speculative fixes and broad dependency upgrades.

4. **Form a hypothesis**
   - State the observed failure, root cause, expected behavior, and smallest safe change.
   - Identify security, compatibility, migration, and regression risks.
   - Define a reproducing test before implementation when feasible.

5. **Implement minimally**
   - Follow existing architecture and naming.
   - Preserve public contracts unless the request explicitly changes them.
   - Add or update focused tests covering the bug, boundary cases, authorization, validation, and failure paths.
   - Never weaken authentication, authorization, CSRF, encryption, audit, or safety controls to make tests pass.

6. **Validate progressively**
   - Run the narrowest relevant test first.
   - Run affected package checks next.
   - Run the repository baseline checks last. For this workspace, normally:
     - `.venv-local\Scripts\python.exe -m pytest -q tests`
     - `npm --prefix frontend run typecheck`
     - `npm --prefix frontend run build`
   - Use the configured project environment, not an unverified global interpreter.
   - Capture command, result, environment, and timestamp.

7. **Diagnose failures**
   - Separate pre-existing failures from regressions.
   - Fix the implementation or test setup; do not hide failures, skip tests, or loosen assertions without evidence.
   - Re-run failed checks after each correction. Stop after three unsuccessful correction cycles and report the blocker.

8. **Review the diff**
   - Check scope, secrets, generated files, migrations, backward compatibility, error handling, and test quality.
   - Confirm no unrelated changes.
   - Re-read changed code against the acceptance criteria.

## Completion criteria

Report:

- Root cause.
- Files changed.
- Fix behavior.
- Tests/checks run, exact commands, environment, timestamp, and results.
- Remaining risks, blockers, or unverified assumptions.

A task is incomplete when tests were not run, a failure is unexplained, or acceptance criteria remain unverified.

## Safety rules

- Ask before destructive, irreversible, production, deployment, data-loss, or credential-affecting actions.
- Do not expose secrets, tokens, private keys, or sensitive test output.
- Do not claim external research or test success without evidence.
- Treat historical reports as context only; current checks are authoritative.
