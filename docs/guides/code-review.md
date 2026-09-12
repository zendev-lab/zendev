# Code review skill

Zendev provides an optional Agent Skill for reviewing code changes. It covers
correctness, security, compatibility, state ownership, and unnecessary complexity.
The repository being reviewed remains the authority for behavior and policy.

The skill lives in
[`skills/code-review/`](https://github.com/zendev-lab/zendev/tree/main/skills/code-review).
Copy the complete directory into your agent's supported skill location, retaining
`SKILL.md` and `references/`. For an agent without skill discovery, explicitly ask
it to read the `SKILL.md` from your local Zendev checkout before reviewing. Installing
the Python package does not install this directory.

For example:

```text
Use code-review to review PR #123. Check correctness and compatibility.
Report findings here; do not modify code or post comments.
```

```text
Read skills/code-review/SKILL.md and review my staged and unstaged changes,
including relevant untracked source files. State what you could verify.
```

Reviews report actionable findings with locations, triggers, impact, supporting
evidence, and a minimal repair direction. The default workflow inspects code and
runs focused non-mutating checks; it does not fix code or post a review. An empty
finding list is limited to the inspected scope and evidence, not a merge decision.

This skill is separate from `zendev message check`, which validates message
structure. It adds no CLI command, model dependency, or CI approval gate.

## Maintaining the skill

Keep the entry point concise and use references for calibration examples and
source rationale. Behavioral cases live in `skills/code-review/evals/evals.json`.
Run them in independent sessions with and without the skill, preserving the same
inputs and model settings. Judge defect detection, false positives, evidence,
and scope discipline; format validation alone does not measure review quality.
