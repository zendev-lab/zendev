---
name: measure-performance
description: >
  Measure and compare latency, throughput, memory, or startup cost with a verified workload and reproducible evidence. Use for “性能测量”, “为什么变慢”, “benchmark 对比”, regression investigation, or validating an optimization. Not speculative optimization, functional test authoring, recurring monitoring, or a claim of improvement based on one unverified timing.
---

# Measure Performance

Define what was measured and prove that both sides completed equivalent work.
A lower number is useful only when workload, correctness, and measurement
boundaries make the comparison meaningful.

## Define the question and baseline

Identify the symptom or proposed optimization, workload, metric, and baseline.
Distinguish user-perceived latency, CPU time, throughput, memory, cold start,
compilation, steady-state execution, and shutdown; do not substitute one for
another. State whether the interval ends at acceptance, response, durable commit,
delivery, or cleanup.

Inspect existing benchmarks, diagnostics, production call paths, and repository
commands before creating instrumentation. Record exact revisions and dirty changes,
build mode, runtime and dependency versions, relevant hardware/backend, workload
size, concurrency, cache state, and timing scope. For a running application, verify
which artifact is actually running instead of assuming it is the current checkout.

Use available authorized resources and bounded workloads. A measurement request
does not authorize paid infrastructure, load against live users, recurring jobs,
or deleting caches and data outside an isolated test environment.

## Establish equivalent work

Check outputs or invariants before timing. Reuse a deterministic correctness case
at a realistic measurement size when possible. Compare equal inputs, outputs,
dtype/layout, model semantics, concurrency, and completion criteria. A backend
that skips work, falls back silently, or produces wrong results is not faster.

Force lazy work to materialize and synchronize asynchronous backends at the chosen
completion boundary. State whether allocation, transfer, parsing, compilation,
I/O, persistence, and cleanup are included. Keep setup outside the interval only
when the question excludes setup. Warmup is appropriate for steady state; it must
not erase a cold-start or first-request regression.

Measure through the real production export or integration path. A microbenchmark
of a replacement helper cannot establish an application-wide improvement. Label
simplified or reduced workloads accurately rather than presenting them as a
standard model or complete user workflow.

## Collect attributable evidence

Use a monotonic duration clock or the repository's benchmark harness. Correlate
events by run/request identity. Keep stage boundaries distinct and account for
overlap: concurrent stage durations cannot simply be added. Do not subtract
timestamps from different processes or clock domains without establishing their
relationship. Missing events leave a gap, not an estimated duration.

Repeat enough to expose variance for the workload and harness; do not impose an
arbitrary universal sample count. Where practical, alternate baseline and candidate
runs to reduce thermal, cache, and background-load bias. Preserve raw samples,
sample counts, units, and the chosen summary statistic. A single run is a sample,
not a latency distribution or evidence for a percentile claim.

Keep instrumentation focused on the uncertain boundary. Prefer durations, counts,
sizes, state transitions, and correlation IDs over logging payloads, credentials,
transcripts, or user content. Account for instrumentation overhead and store run
artifacts separately from normative project documentation.

## Interpret before optimizing

Compare under matched conditions and report absolute values alongside relative
change. Explain the denominator, direction of improvement, variation, and missing
coverage. Do not cherry-pick the fastest run, silently discard failures, or combine
different workloads into one speedup. Distinguish CPU simulation, local walltime,
hosted benchmark results, and device observations; disagreement needs investigation.

Use profiles or stage evidence to identify the dominant cost before changing the
implementation. A faster local result does not cancel an unresolved hosted
regression. Do not weaken thresholds, correctness checks, privacy protections, or
completion semantics to manufacture a passing comparison.

For diagnosis, stop at the evidence-backed cause or bounded hypotheses. When an
optimization is requested, make the smallest justified change at the responsible
owner, rerun correctness checks, and repeat the comparable measurement. Include
tradeoffs such as higher memory, delayed durability, or worse tail latency.

## Deliver the result

Give the measured question, baseline and candidate identities, workload and
environment, timing boundaries, sample counts and results, and reproducible
commands or artifact paths. State which conclusions the data supports and what
remains unmeasured. An unavailable backend, failed run, or non-comparable environment
is a limitation, not an invented result or proof that performance is unchanged.
