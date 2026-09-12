# Design sources

Reviewed on 2026-09-12. These notes explain design choices; they are not additional
runtime instructions, copied prompts, or evidence of model-specific performance.
The skill uses original wording and remains independent of a provider or harness.

| Source | Adopted | Deliberately omitted |
| --- | --- | --- |
| Author's existing `vet` skill | Concrete failure modes, API verification, duplicate consolidation, behavior-oriented tests | Automatic cleanup during a review; a mandatory full baseline suite |
| [Spark code review](https://github.com/zendev-lab/spark/blob/main/.agents/skills/spark-code-review/SKILL.md) | Authoritative state ownership, cross-component contracts, concrete costs of extra abstractions | Spark-only companion skills and mandatory report fields irrelevant to a small review |
| [Anthropic PR review toolkit](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/pr-review-toolkit/agents/code-reviewer.md) | Explicit scope, aggressive false-positive filtering, precise evidence and repair direction | Numeric confidence thresholds that mix likelihood with impact; an unstaged-only default |
| [Superpowers requesting-code-review](https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md) | Exact revisions and requirements for independent review; technical verification of reviewer feedback | Mandatory delegation and automatic repair as part of every review |
| [GPT-6 Astra model guidance](https://developers.openai.com/api/docs/guides/latest-model) | Explicit completion boundary, proportionate verification, clear output expectations | Hardcoded effort settings, prescribed agent counts, and generic implementation instructions |
| [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | Short trigger description, contextual references, task-relevant instructions | A long mandatory itinerary or broad trigger keywords |
| [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1) | Brief progress updates, independent read batching, explicit scope and completion limits | API history/cache mechanics, unrelated edits, and provider-specific runtime configuration |

The local `vet` skill was read from the author's skill library; it is not a runtime
dependency or a file consumers need to install. Sources can evolve. Revisit the
specific source when changing the relevant behavior rather than loading every
reference on each review.
