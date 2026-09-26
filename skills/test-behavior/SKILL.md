---
name: test-behavior
description: >
  Add or repair tests that demonstrate an observable contract, regression, state transition, or backend equivalence. Use for “补测试”, “回归测试”, flaky ordering tests, cancellation and persistence checks, numerical reference comparisons, or compiler/backend parity. Not a coverage-percentage campaign, benchmark workflow, full code review, or a requirement to test every cosmetic edit.
---

# Test Behavior

Build a test that distinguishes the intended behavior from a plausible defect.
The tested boundary and observable result matter more than the number of cases,
mocks, assertions, or covered lines.

## Choose the contract and observation

Read the requirement, affected production caller, nearest tests, and repository
test commands. Identify the input or event ordering, expected result, and defect
the test must detect. Use an existing fixture or test owner when it already models
that boundary; do not create a parallel harness without a demonstrated need.

Choose the narrowest level that can observe the failure. A pure transformation
can use a unit test; ownership, persistence, process, serialization, or UI defects
may need the real boundary. A test that replaces the faulty integration with a
mock cannot prove that integration. Keep normal execution deterministic and use
isolated data rather than user databases, credentials, or live accounts.

For a regression, demonstrate failure against the faulty behavior when practical,
then success after the fix. Use an isolated reproduction or fixture; do not revert
unrelated work. If the old failure cannot be executed, explain the limitation and
show how the assertion discriminates it. Do not invent a red/green result.

## Assert outcomes rather than implementation shape

Assert returned values, externally visible state, committed data, ordered effects,
diagnostics, or cleanup. A boundary call count is useful when “at most once” is the
actual contract; internal helper calls alone are usually incidental.

Do not match source fragments, prompts, comments, or private call structure to
prove behavior. Parse structured output and assert its meaning. Exact bytes,
snapshots, messages, or hashes are appropriate when the representation itself is
the intentional contract, such as a wire format, rendered artifact, or integrity
digest; explain that boundary and keep the assertion scoped to it.

Choose cases from reachable distinctions: success, invalid input, empty or boundary
values, failure and partial effects, cancellation, replacement, or restart. Include
only those that exercise different behavior. Do not mechanically apply the entire
list to every function or duplicate coverage already provided by a clearer test.

## Control asynchronous ordering

Use a barrier, controllable fake, injected clock, or lease to stop at the vulnerable
boundary. Wait for the operation to enter it, trigger the competing event, release
the operation, and observe both the result and the remaining resources or tasks.
Bound waits and release or dispose resources even when an assertion fails.

Distinguish accepted, committed, published, and drained work. For replacement or
cancellation, check that a retired operation cannot publish a stale result while
its cleanup is still retained. Use a fake that ignores cancellation when that is
allowed by the real dependency. Do not “fix” a race test by increasing a sleep,
adding blind retries, or assuming cancellation already finished cleanup.

Control time and randomness only where they are inputs to the behavior. Keep at
least the necessary real scheduler, storage, or process boundary when that is what
the test is intended to establish. A fake-clock test does not establish real device
latency or OS event delivery.

## Use independent references for computation

For numerical results, compare against a small trusted reference, explicit values,
or independently derived properties. Match dtype, shape, layout, device, seed,
and model semantics. Select tolerances from the operation and numerical precision;
do not loosen them merely to make a failing backend pass. Cover relevant zeros,
non-finite values, broadcasting, and gradients when these are part of the change.

For compilers or multiple backends, compare semantic outcomes and required failure
behavior on the same supported input. Parser success, type checking, interpretation,
native execution, and artifact loading are distinct claims. Parity alone can miss
a shared bug, so include a known expected result or independent property where
possible. Reusing the production algorithm to compute expected results weakens
the test even when it lives in a separate file.

## Run and report

Run the focused case and the relevant existing suite, then the gates required by
the repository. Investigate a failing test instead of silently skipping it or
updating snapshots. A backend that did not run is untested; a skip is not a pass.

Report the covered contract, executed commands and results, and material gaps.
Separate unit evidence from hosted CI, installed-package checks, and physical
device or UI acceptance. Do not claim complete correctness from a green suite or
add low-value tests solely to improve a percentage. Preserve repository coverage
requirements while keeping assertions tied to behavior.
