# Maintain a repository proposal skill

A repository proposal skill gives an agent the task-specific judgments and
local entry points needed to prepare a design record. Start with
[proposal writing](proposal-writing.md), then adapt to the repository's actual
governance. Zendev supplies guidance and validation tools; repositories retain
their own decision process.

## Find the existing owner

Read existing skill names, descriptions, and agent instructions before adding
an entry. Extend an existing design or feature-planning skill when it already
owns this result. Create a separate proposal skill only when that task has no
appropriate owner. General project planning and Git delivery keep their own
responsibilities.

Inspect these sources before writing the instructions:

| Source | What the skill must discover or preserve |
| --- | --- |
| Governance and contribution guide | Proposal threshold, decision authority, review and implementation boundaries |
| Templates and schema | Required content, identity, numbering, status, and author representation |
| Related proposals and glossary | Existing decisions, dependencies, terms, and amendment rules |
| Source and tests | Current behavior and the affected consumers |
| Validation configuration | Supported check, repair, and index-generation entry points |
| Agent instructions and skills | Discovery route and the current task owner |

Do not assume ZFP conventions. One repository may number drafts immediately;
another assigns numbers at acceptance. Some keep acceptance states, while
others deliberately omit them. These differences must come from the owning
repository, not from this guide.

## Write a small task procedure

Use the host's supported skill format. For Agent Skills, put `SKILL.md` in the
repository's established skill directory, with `name` and `description`
frontmatter. Describe the task and its nearest exclusions, such as routine bug
fixes or implementation of a settled design. Avoid routing every code change
through proposal authoring.

The following body illustrates the decisions to cover. Replace its prose
references with real repository-relative links and apply the host's naming and
discovery conventions; it is not an additional proposal template.

> Assess the change using the governing proposal and current implementation.
> Reuse an existing decision where it covers the work.
>
> Research meaningful alternatives. Ask about unresolved choices that affect
> scope, behavior, ownership, compatibility, or authority before selecting a
> direction. Reuse prior decisions; record explicit delegation when applicable.
> Continue independent work while a key answer is pending.
>
> Write in the repository template. Preserve its metadata, numbering,
> terminology, and lifecycle. Make actors, conditions, failure behavior, and
> acceptance criteria explicit without inventing missing requirements.
>
> Run the contribution guide's checks, inspect generated changes, and report
> evidence and unresolved decisions. The request's scope determines whether
> the result is a review, a draft, or implementation work.

Retain the local reading links and essential judgments in the skill so an agent
can use it without fetching this website. Do not copy the full guide, maintain
a second schema in prose, or require a global personal skill installation.
Discover evolving CLI syntax from the actual version and existing repository
commands. A missing tool leaves validation incomplete; it does not authorize
installing a new governance system.

Keep author-facing sources, installation instructions, and evaluation answers
outside the runtime skill. Add reference files only for knowledge needed while
performing the task. Do not introduce fixed models, agent counts, or host APIs
unless the repository's existing runtime contract requires them.

## Connect discovery

Link the entry from the repository's existing agent or contribution navigation.
If a planning skill already has callers, preserve its name and output contract.
For example, a caller that receives a structured unresolved-decision result
must still know that no user choice has been obtained.

The writing guide and this adaptation guide are available from the generated
`llms.txt` and as per-page Markdown in the documentation site. They are
maintenance resources, not a network prerequisite for every proposal task.

## Validate behavior

Check frontmatter, relative links, discovery, and any repository knowledge
budgets. Then use realistic requests that can reveal wrong decisions:

- A routine fix that restores a documented behavior should follow the local
  exemption, rather than acquire an unnecessary proposal.
- A material choice with no user decision should produce an actual question
  or the host's existing handoff, not an assumed selection.
- A task with an explicit prior choice should reuse it.
- A requested draft with an ambiguous retry count should retain the gap until
  evidence or a decision resolves it.
- A measured duration should remain an observation, rather than become a
  guaranteed deadline to satisfy a wording rule.
- A concise, structurally valid draft with an unsupported guarantee should
  still be corrected or reported as incomplete.
- A task in another repository should preserve that repository's authorship,
  numbering, lifecycle, and checker.

Inspect whether the resulting document lets a reader identify the decision,
its evidence, and the behavior of a representative case and a relevant
exception. Use the same source material and reader task when comparing skill
versions; count invented or lost facts separately from presentation issues.
Do not test prompt substrings as a substitute for these outcomes.
Keep structure checks, author walkthroughs, independent execution, and
comparative evaluations distinct in the report.
Only claim an improvement when comparable runs support it.
