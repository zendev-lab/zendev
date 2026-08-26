---
zfp: 0
title: "Zendev Feature Proposal Governance"
status: Draft
type: Governance
authors:
  - "zrr1999"
created: 2026-08-26
supersedes: []
---

# ZFP-0000: Zendev Feature Proposal Governance

## Summary

Every public zendev feature begins with a lightweight Zendev Feature Proposal.
The proposal records the decision; Git and its pull request record discussion
and acceptance.

## Motivation

Zendev now owns multiple CLI workflows and repository policies. Small design
records keep public contracts reviewable without introducing a database,
approval service, or heavyweight status process.

## Design

A ZFP is required for a new CLI or option, public Python API, configuration or
schema format, packaging boundary, or user-visible workflow behavior. Bug fixes
that restore an accepted contract, tests, documentation, dependency maintenance,
and internal refactors without public behavior changes are exempt. When in doubt,
write the short proposal.

Each ZFP uses the repository template and begins as `Draft` in a proposal-only
pull request. After review reaches a decision, a later commit changes the same
document to `Accepted`; only then may the pull request merge. Rejected or
withdrawn candidates remain closed pull requests as `Draft` instead of entering
the canonical branch. An implementation may be prepared as a dependent draft
pull request, but it must reference the accepted ZFP before it lands.

Accepted decisions remain in Git. A replacement ZFP updates the prior record to
`Superseded` and names it in `supersedes`; editorial corrections may update a
record without changing its decision. ZFP-0000 follows the same transition it
defines.

## Compatibility

The process applies only to feature work proposed after ZFP-0000. Existing
behavior and pull request #12 are not retroactively required to add proposals.

## Validation

`zendev-proposal check` validates ZFP metadata, required sections, relations,
every committed status transition when a base ref is supplied, and the
deterministic index. Repository hooks run the same check without attempting to
classify implementation diffs.
