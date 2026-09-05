# Repository-native development

Repository-native workflows keep their durable state in Git. A contributor can
inspect a rule and its result from a checkout without depending on a separate
database or service.

For proposals, the flow is:

```text
Markdown + YAML frontmatter + repository policy
                    ↓
          deterministic validation
                    ↓
             committed JSON index
```

For commit and pull-request messages, the repository configuration and PR
template define the contract, while zendev produces deterministic validation
results.

## What zendev does not own

Zendev does not decide whether a proposal should be accepted, store a proposal
lifecycle in a service, or replace review. It validates the repository's chosen
representation. Git history remains the record of how that representation
changed.

This also applies to the documentation site: Markdown under `docs/` is the
source, Zensical validates and projects it into static HTML, and the generated
`site/` directory is disposable.
