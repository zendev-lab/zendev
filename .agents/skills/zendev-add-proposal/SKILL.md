---
name: zendev-add-proposal
description: >
  Assess whether a change needs a durable design proposal under repository policy, research alternatives and ask the user about unresolved key choices before writing or materially revising it, or review it with zendev validation. Use for “是否需要提案”, “写提案”, “修改提案”, RFC/ZFP review, or a new public-contract or consequential design decision. In Zendev, new public interfaces follow ZFP-0000 even when compatible. Routine fixes restoring existing behavior and implementation of settled decisions do not need another proposal. Do not use for routine implementation, project planning, evolution logs, or Git delivery.
---

# Zendev Add Proposal

Keep the reasoning for consequential design decisions reviewable and durable.
The first result is a decision about whether a proposal is needed. Creating a
proposal file is conditional, not the default outcome of loading this skill.

## Establish the impact

For work in Zendev itself, first read
[ZFP-0000](../../../zfps/ZFP-0000-governance.md) and the
[submission guide](../../../zfps/README.md). They require proposals for new public
contracts, including compatible new interfaces. In another repository, discover
its corresponding policy; these Zendev-relative links are not portable
installation dependencies. Apply the known local threshold before the general
impact guidance below.

Read the requested change, affected implementation and consumers, applicable
repository guidance, and existing proposals. Identify the behavior before and
after, who depends on it, and the practical cost of migration or reversal.
Do not classify from a title, commit type, line count, or number of files.

Where repository policy does not define the threshold, require a proposal only
when there is both a new decision not already covered by an existing proposal
and clear evidence of substantial impact. Substantial impact means consequences
such as:

- Breaking a supported API, CLI, configuration, protocol, or data contract so
  existing consumers must migrate or coordinate their rollout.
- Materially changing a core default or workflow relied on by users, including
  consequential changes to data retention, privacy, authorization, or trust.
- Moving persistent state or resource ownership, changing package or subsystem
  responsibilities, or introducing a long-lived dependency in a way that requires
  coordinated changes or makes recovery and reversal substantially harder.
- Changing important project-wide release, compatibility, governance, or decision
  authority rules with lasting consequences for contributors or consumers.

These are impact tests, not keyword triggers. A change to one internal owner or
one governance sentence is not automatically substantial. Name the affected
consumers, changed guarantee, and migration, coordination, or recovery burden.
One concrete serious consequence can be sufficient; several speculative risks
do not become evidence merely by being listed together.

Under this fallback impact threshold, ordinary additive features, compatible
optional parameters, aliases using existing semantics, local refactors, tests,
documentation, and routine dependency updates normally proceed directly.
A new interface alone is not sufficient under that threshold. Conversely,
a small diff or an optional feature can have substantial impact, for example by
introducing a new boundary for sensitive data. Judge its actual consequences.

Implementing an existing proposal does not need another proposal, even if the
implementation is large. Link the existing decision; reassess only genuinely new
choices outside its scope. Do not split one decision into a proposal per stage.

When local policy leaves the decision to impact and the evidence does not
establish it, do not create a proposal as a precaution. Explain the specific
uncertainty and inspect the missing facts;
ask only if an unresolved answer changes the route. Continue independent work
within the user's scope. Do not invent consumers, migration costs, or risk to
justify a proposal. A user may explicitly request a design draft for a small
change; write it without claiming that the change requires formal governance.

## Apply repository policy

Find the authoritative governance document, contribution guide, proposal
configuration, schema, template, and relevant existing records. Reuse their
location, identifiers, metadata, and lifecycle instead of imposing ZFP conventions
on every repository. Installation copies of this skill need no sibling files.

If an explicit repository rule requires proposals more broadly than the general
impact guidance, apply it and distinguish policy compliance from a finding of
substantial impact. Do not ask the user to reconfirm an unambiguous local rule.
Clarify only a missing or contradictory rule that affects the route, or a conflict
with the user's current instruction. Do not silently rewrite repository governance.

State the route briefly: direct implementation, an existing proposal, or a new
proposal, with the decisive evidence. A request to assess or review does not
authorize implementing the design or creating a file. A requested proposal already
authorizes drafting; do not ask for that permission again. This does not resolve
the design choices that must be discussed below.

## Research and ask before choosing

Before writing a new proposal or materially revising its design, research the
decision and ask the user about unresolved key choices. This also applies to an
explicitly requested small design draft; it does not broaden the proposal threshold.

Read the owning implementation, tests, existing decisions, and relevant alternatives.
For external approaches, dependencies, or APIs, verify current primary sources such
as official documentation, source code, or papers. Record sources and applicable
versions; distinguish observations from assumptions and inference. If evidence is
unavailable, identify the gap and continue only work independent of that evidence.
Do not invent findings or ask the user to retrieve facts available to the agent.

Identify choices that change scope, public behavior, ownership, compatibility,
migration, privacy, governance, or long-term cost. Present viable alternatives,
including the status quo where relevant, with a recommendation, supporting evidence,
and the main tradeoffs. Ask the root choices before questions that depend on them;
do not manufacture alternatives just to fill an option list.

Actually ask and obtain these choices before treating a direction as decided;
an open-question list or the agent's recommendation is not a user decision. Do
not defer the questions until a complete proposal has already fixed the direction.
Reuse explicit choices already supplied by the user or established by applicable
decisions, citing their basis instead of asking again. If the user explicitly
delegates a choice, decide within the stated constraints and record that delegation
and rationale. A request to write a proposal alone is not such delegation.
Resolve routine reversible details independently, without relabeling key design
choices as implementation details.

While waiting, continue independent research or draft unaffected sections. Mark
dependent alternatives as unresolved; silence does not select the recommendation.
Do not finalize those decisions or implement their dependent behavior. Editorial
corrections and implementation of existing decisions do not reopen settled choices.

## Write the decision

Use the repository template and put the following reasoning in its existing
sections; do not add a second mandatory outline:

- The concrete problem and current behavior, supported by source or observed facts.
- The proposed behavior, ownership and interfaces, including what is outside scope.
- The meaningful alternatives, including retaining the current behavior, and why
  the chosen direction earns its migration and maintenance cost.
- Research evidence and the basis of each key selection: the user's answer, an
  applicable existing decision, or an explicitly delegated choice with its rationale.
- Compatibility, affected consumers, rollout and recovery where relevant, and
  observable checks that would establish the intended result.

Use the project's preferred term for each concept and link its existing definition.
Make actors, objects, condition scope, counting boundaries, and failure behavior
explicit where they affect the decision. Preserve negation, exceptions, ordering,
and uncertainty when editing. Ask about missing semantics instead of completing
them by guesswork. Distinguish required behavior from recommendations using local
conventions; proposed behavior and future acceptance criteria are not measured
results. Use connected prose for reasoning and steps only for ordered actions.

Scale detail to the decision. Preserve uncertainties as open questions instead
of fabricating requirements or presenting a draft as accepted. Separate document
validation, acceptance, implementation, and release according to local policy;
merging a document does not by itself prove the feature is approved or shipped.

For revisions, preserve existing identifiers and history. Distinguish editorial
corrections from changed decisions; use the repository's revision or supersession
rules for the latter. Do not guess author identities, dates, or proposal numbers.
Resolve them from repository evidence or ask for the missing fact.

## Validate and deliver

Read the draft without relying on the conversation. Trace a representative case
and a relevant boundary or failure through its proposed behavior; check that
the stated conditions lead to the stated result. Compare important claims with
their sources. Preserve units, range endpoints, and the distinction between a
measurement, an estimate, a target, and a guarantee. Language-checker findings
require contextual review and do not establish factual or design correctness.

Use the repository's existing validation command. For zendev repositories, discover
exact syntax through the installed `zendev proposal --help` and subcommand help.
Run a read-only check first. When editing proposals, use supported repair or index
generation only for the intended changes, inspect the complete diff, and rerun
the check. Do not manually fabricate an index or let repairs rewrite unrelated
records. Missing tools or configuration leave validation incomplete; they do not
justify installing tools or initializing a governance system without scope.

Report the impact decision, research and key choices, document location if one was
written, actual checks, and unresolved questions. A schema pass proves structure,
not design acceptance or that a proposal was necessary. Project planning and evolution records retain
their own owners; Git topology, proposal/implementation PR separation, and delivery
follow the repository workflow and the user's authorized endpoint.
