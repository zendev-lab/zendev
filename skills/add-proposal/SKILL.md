---
name: add-proposal
description: >
  Assess whether a change has enough impact to need a durable design proposal, then write, revise, or review it using the repository's proposal policy and zendev validation. Use for “是否需要提案”, “写提案”, “修改提案”, RFC/ZFP review, or a new design decision with substantial compatibility, migration, ownership, privacy, or governance consequences. Ordinary features, compatible options, aliases, bug fixes, and internal refactors do not trigger proposals merely because they change code or expose an interface. Do not use for routine implementation, project planning, evolution logs, or Git delivery.
---

# Add Proposal

Keep the reasoning for consequential design decisions reviewable and durable.
The first result is a decision about whether a proposal is needed. Creating a
proposal file is conditional, not the default outcome of loading this skill.

## Establish the impact

Read the requested change, affected implementation and consumers, applicable
repository guidance, and existing proposals. Identify the behavior before and
after, who depends on it, and the practical cost of migration or reversal.
Do not classify from a title, commit type, line count, or number of files.

Require a proposal only when there is both a new decision not already covered
by an existing proposal and clear evidence of substantial impact. Substantial
impact means consequences such as:

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

Ordinary additive features, compatible optional parameters, aliases using existing
semantics, local refactors, tests, documentation, and routine dependency updates
normally proceed directly. A new interface alone is not sufficient. Conversely,
a small diff or an optional feature can have substantial impact, for example by
introducing a new boundary for sensitive data. Judge its actual consequences.

Implementing an existing proposal does not need another proposal, even if the
implementation is large. Link the existing decision; reassess only genuinely new
choices outside its scope. Do not split one decision into a proposal per stage.

When the evidence does not establish substantial impact, do not create a proposal
as a precaution. Explain the specific uncertainty and inspect the missing facts;
ask only if an unresolved answer changes the route. Continue independent work
within the user's scope. Do not invent consumers, migration costs, or risk to
justify a proposal. A user may explicitly request a design draft for a small
change; write it without claiming that the change requires formal governance.

## Apply repository policy

Find the authoritative governance document, contribution guide, proposal
configuration, schema, template, and relevant existing records. Reuse their
location, identifiers, metadata, and lifecycle instead of imposing ZFP conventions
on every repository. Installation copies of this skill need no sibling files.

If an explicit repository rule requires proposals more broadly than the impact
threshold above, state the concrete conflict and distinguish policy compliance
from a finding of substantial impact. Follow the user's current instruction when
it resolves that conflict. Otherwise clarify only the conflicting requirement;
do not silently broaden this skill's threshold or rewrite repository governance.

State the route briefly: direct implementation, an existing proposal, or a new
proposal, with the decisive evidence. A request to assess or review does not
authorize implementing the design or creating a file. For a requested proposal,
prepare the document without asking for another approval of the same work.

## Write the decision

Use the repository template and put the following reasoning in its existing
sections; do not add a second mandatory outline:

- The concrete problem and current behavior, supported by source or observed facts.
- The proposed behavior, ownership and interfaces, including what is outside scope.
- The meaningful alternatives, including retaining the current behavior, and why
  the chosen direction earns its migration and maintenance cost.
- Compatibility, affected consumers, rollout and recovery where relevant, and
  observable checks that would establish the intended result.

Scale detail to the decision. Preserve uncertainties as open questions instead
of fabricating requirements or presenting a draft as accepted. Separate document
validation, acceptance, implementation, and release according to local policy;
merging a document does not by itself prove the feature is approved or shipped.

For revisions, preserve existing identifiers and history. Distinguish editorial
corrections from changed decisions; use the repository's revision or supersession
rules for the latter. Do not guess author identities, dates, or proposal numbers.
Resolve them from repository evidence or ask for the missing fact.

## Validate and deliver

Use the repository's existing validation command. For zendev repositories, discover
exact syntax through the installed `zendev proposal --help` and subcommand help.
Run a read-only check first. When editing proposals, use supported repair or index
generation only for the intended changes, inspect the complete diff, and rerun
the check. Do not manually fabricate an index or let repairs rewrite unrelated
records. Missing tools or configuration leave validation incomplete; they do not
justify installing tools or initializing a governance system without scope.

Report the impact decision, document location if one was written, actual checks,
and unresolved questions. A schema pass proves structure, not design acceptance
or that a proposal was necessary. Project planning and evolution records retain
their own owners; Git topology, proposal/implementation PR separation, and delivery
follow the repository workflow and the user's authorized endpoint.
