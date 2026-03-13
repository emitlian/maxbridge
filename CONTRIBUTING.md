# Contributing to MAXBRIDGE

Thank you for contributing to MAXBRIDGE.

This repository is intentionally scoped as local-first interoperability infrastructure for MAX with Telegram forum mirroring, archive and replay tooling, and an owner-only Telegram control plane. Contributions should reinforce that scope rather than broaden the project into bulk messaging or opaque automation.

## Project Principles

- local-first state, storage, and recovery
- deterministic bridge behavior backed by SQLite mappings
- clear separation between stable core modules and experimental MAX adapters
- owner-controlled automation only
- honest documentation about what is implemented, what is experimental, and what is out of scope

## Stable Core And Experimental Layers

Stable core areas:

- `maxbridge.config`
- `maxbridge.core` interfaces and typed models
- `maxbridge.storage`
- `maxbridge.archive`
- `maxbridge.bridge`
- `maxbridge.telegram`
- `maxbridge.cli`

Experimental areas:

- `maxbridge.experimental`
- `maxbridge.auth`
- adapters that depend on unsupported or unstable upstream MAX capabilities

If you touch experimental modules, document the boundary clearly and avoid presenting those integrations as production-ready.

## Before You Open A Pull Request

1. Read the README and architecture notes to understand the local-first bridge model.
2. Check whether the change belongs in the stable core or the experimental adapter layer.
3. Prefer small, reviewable pull requests over broad rewrites.
4. Preserve public behavior unless a narrow compatibility-safe refactor is clearly justified.
5. Add or update tests for storage behavior, routing, archive flows, or bridge behavior when applicable.

## Contribution Checklist

Use this checklist before requesting review:

- the change fits the project scope and does not introduce spam, bulk messaging, hidden automation, or unauthorized account access features
- stable core changes stay production-minded and keep experimental logic isolated
- new comments and docstrings are written in clear English
- new user-facing text uses a normal hyphen instead of an em dash
- non-obvious logic has explanatory comments or docstrings
- docs and examples are updated when behavior or workflows change
- tests were added or updated where the change affects storage, bridge mappings, routing, replay, or Telegram control behavior
- `pytest -q` passes locally
- `ruff check .`, `ruff format --check .`, and `mypy maxbridge` pass locally when the change affects Python code

## Pull Request Guidance

Please include:

- a short summary of the user-visible change
- the architectural area affected, such as storage, bridge sync, archive, or Telegram control plane
- any schema, mapping, or migration impact
- any stability impact, especially if the change touches experimental adapters
- the exact commands you ran for validation

## Reporting Bugs

When reporting a bug, include enough detail for a maintainer to reproduce the issue locally:

- configuration shape, with secrets removed
- relevant CLI command or control-plane action
- expected behavior
- actual behavior
- logs or stack traces, with secrets removed
- whether the issue came from the stable core or an experimental adapter

## Good First Contribution Areas

- archive schema improvements
- replay fixtures and integration tests
- storage inspection commands
- Telegram forum formatting and owner-only UX
- docs, examples, and onboarding improvements

## Out Of Scope Contributions

The following will generally not be accepted:

- mass messaging features
- stealth automation
- hidden authentication flows
- unauthorized account access workflows
- bypasses for protected or private APIs
- cloud-first control layers that replace the local-first model

## Questions

If your change crosses the stable core and experimental adapter boundary, explain the reasoning explicitly in the pull request so reviewers can evaluate the trade-offs quickly.
