---
name: code-style
description: >
  Write or reshape code to match the repository's conventions while keeping types, ownership, control flow, and effects easy to follow. Use for “代码风格”, “按项目风格写”, naming and API shape, simplifying a local implementation, or applying a shared coding baseline across languages. Not a repository-wide architecture audit, correctness review, formatter migration, or technology-selection workflow.
---

# Code Style

Make the implementation readable from its domain model and execution path.
Preserve behavior during style cleanup; an intentional behavior change needs its
own rationale and verification. Apply this guidance to the requested scope, not
as a reason to rewrite neighboring code.

## Establish the local baseline

Read applicable instructions, formatter and lint configuration, language version,
and a few representative files in the owning module, including callers and tests.
Prefer enforced configuration and explicit contracts over an isolated code sample.
Existing code may contain debt; do not reproduce a bug or an obsolete workaround
just to resemble it.

Keep the repository's indentation, line width, imports, naming, and documentation
conventions. Do not transplant one reference project's settings into another or
introduce a second formatter. Use English identifiers and code comments unless
the project specifies otherwise; user-facing prose follows its audience.

## Express the domain directly

- Name values and operations for their meaning, units, and effects. Distinguish a
  request from an attempt, an accepted write from a committed write, and a duration
  from a timestamp when the distinction affects callers. Avoid generic Manager,
  Service, or Utils names when a specific responsibility is available.
- Use existing domain types. Prefer enums or tagged unions for mutually exclusive
  states and records for related values; avoid combinations of booleans and nullable
  fields that permit impossible states. Do not add a new wrapper for every primitive.
- Keep absence, invalid input, cancellation, unsupported capability, and failure
  distinct when callers must react differently. Do not turn unknown into empty,
  false, or success merely to satisfy a type or shorten a branch.
- Keep pure transformations separate from I/O and policy decisions when it makes
  effects testable. A helper should name a coherent operation or invariant, not
  obscure a few lines that are clearer at the call site.

## Keep ownership and dependencies visible

Find the existing owner before introducing a store, cache, queue, scheduler, or
state machine. Adapters translate input and output through that owner's API;
presentation code should not reconstruct authoritative state from logs or timers.
Derive projections when possible instead of maintaining synchronized copies.

Keep dependencies directed toward domain contracts. Assemble concrete resources
at the composition boundary and pass the narrow values or capabilities a consumer
needs. Avoid passing a whole application context to a small operation. An interface
with one implementation can still be useful for a real effect or test boundary;
implementation count alone does not justify adding or removing it.

Extract a module for a distinct responsibility, invariant, or effect boundary.
Do not split a transaction owner merely because a file is long, or create a package
to hide a few helpers. Consolidate genuinely shared semantics in their existing
owner; similar-looking code with different contracts need not share an abstraction.

## Make control flow and effects explicit

Use straightforward branches and early exits where they reduce nesting. Keep the
normal path legible; avoid clever expressions and layered callbacks that hide the
order of mutation. Prefer immutable inputs and bounded local mutation over shared
mutable state, without forcing costly copies or a framework onto simple code.

Validate at trust and representation boundaries, then carry the validated type
inward. Retain checks whose inputs can change across a wait, transaction, process,
or permission boundary. Do not erase authorization or safety checks as redundant.
Catch errors where they can be translated, recovered, or given useful context;
preserve their cause. A fallback must be part of the intended behavior, not a way
to conceal invalid required configuration or a programming error.

Keep task, resource, and cleanup lifetimes with an explicit owner. Cancellation
requests termination; it does not prove completion. Preserve identity checks after
suspension and retain accepted work until it can be awaited or drained. Avoid
detached tasks, broad retries, or arbitrary delays used to hide lifecycle mistakes.

## Respect the language and boundary

Apply only the relevant language guidance, using the project's supported version:

- **TypeScript:** narrow external `unknown` values once, use discriminated unions
  for outcomes, and keep wire validation aligned with the canonical schema. Avoid
  `any`, unchecked casts, and non-null assertions used to bypass an unresolved
  invariant; a justified boundary assertion can remain local and documented.
- **Swift:** use value types for values and explicit isolation for shared state.
  Make actor hops, task ownership, cancellation, and stale-result checks visible.
  Do not assume actor isolation makes a transaction atomic across suspension.
- **Python:** use concrete annotations and small records where they clarify the
  contract; preserve exception types and causes. Avoid broad exception suppression,
  untyped dictionaries for known domain shapes, and ambient mutable configuration.
- **Rust:** model outcomes with enums and `Result`, borrow or move deliberately,
  and keep `unsafe`/FFI assumptions local and documented. Do not add cloning, shared
  locks, or production panics simply to bypass ownership and error design.
- **Cross-language boundaries:** make buffer lifetime, shape, dtype, ownership
  transfer, encoding, and error translation explicit. A conversion that compiles
  does not establish ABI compatibility or semantic equivalence.

Comments explain non-obvious reasons, invariants, units, or compatibility limits.
Preserve useful public API documentation; remove narration of obvious code and
stale explanations. Use data or declarative configuration for genuine tables and
policies, without turning ordinary control flow into a configurable framework.

## Verify the change

Use the repository's existing formatting, lint, and type checks. Read the resulting
diff for accidental semantic changes and unrelated formatting. Run focused tests
when control flow, types, resource lifetime, or observable behavior changed; do not
add tests that merely match source wording. Existing contract tests can be enough
for a behavior-preserving cleanup.

Report the concrete simplification and checks performed. Broader architecture
decisions, defect reviews, test design, performance claims, and Git delivery remain
separate tasks; do not declare code correct or faster from stylistic consistency.
