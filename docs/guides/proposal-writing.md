# Write a reviewable proposal

A proposal should let a reviewer understand the problem, compare the available choices, and judge the resulting contract. Use this guide when drafting or materially revising a design record. It supplements the repository's governance and template; it does not introduce a proposal threshold or approval process.

For document and index validation, see [Proposals](proposals.md). To turn these methods into a repository task procedure, see [Repository proposal skills](proposal-skills.md).

## Establish the decision

Read the governing proposal, contribution guide, affected implementation and tests, and related decisions. Determine which existing guarantee changes, who depends on it, and what migration or coordination follows. Apply the repository's threshold: a new interface may require a proposal in one project while another requires evidence of substantial impact. Neither diff size nor a commit label settles this question.

State whether the work follows an existing decision, needs a new proposal, or can proceed directly. A requested design draft may still be useful below the formal threshold. Adding writing guidance or a skill that follows existing policy does not itself change that policy; changing decision authority or the threshold is a separate governance decision.

## Research before selecting

Describe the current behavior using source, tests, or observed results. For external approaches, consult primary documentation, source code, or papers and record the applicable version. Keep observations distinct from inferences and unverified assumptions. Missing evidence is a gap to investigate, not a reason to invent a requirement.

Compare viable alternatives against the actual constraints, including keeping the current behavior when that is meaningful. Explain the benefit and cost of each option: ownership, compatibility, recovery, maintenance, or other concerns that can change the decision. Do not fill a comparison table with implausible alternatives.

Before fixing the direction, ask the user about unresolved choices that change scope, public behavior, authority, migration, or long-term cost. Present the evidence, recommendation, and tradeoffs. Reuse explicit prior choices and applicable decisions without asking again. When the user delegates a choice, record the delegation and the rationale. Resolve routine reversible details without turning them into approval steps.

An instruction to write the proposal authorizes drafting; it does not select every design option. While awaiting a key answer, continue independent research or unaffected sections. Leave dependent alternatives unresolved. An unanswered question or a recommendation is not agreement.

## Describe behavior precisely

Use the repository's existing sections. Give each part a purpose rather than adding another mandatory outline:

| Reviewer's question | Evidence to include |
| --- | --- |
| What problem exists? | Current behavior, affected users, and a concrete example |
| What changes? | Proposed behavior, responsible component, inputs, outputs, and relevant failure cases |
| Why this choice? | Alternatives, tradeoffs, and the source of the decision |
| Who must adapt? | Compatibility, migration, rollout, and recovery where applicable |
| What would prove it? | Observable acceptance criteria and limits of the available evidence |

Use the same preferred term for the same concept. Consult the project glossary before introducing a name, and explain unfamiliar terms at first use. Preserve literal identifiers, API names, and quoted source material. A glossary entry or definition anchor belongs in the location required by local policy.

Name the actor and object when their identity affects the contract. Keep conditions, negation, quantifiers, ordering, exceptions, and uncertainty intact. Shortening a sentence must not change which action a condition controls.

For numerical claims, identify the unit, comparison baseline, and whether a limit includes its endpoint where these affect the decision. Keep observations, estimates, targets, and guarantees distinct: a request measured at about five seconds does not establish a five-second upper bound. Resolve ambiguous limits from evidence or a decision before rewriting them as exact requirements.

For example, this sentence leaves both the actor and the counting rule unclear:

> 校验失败后重新提交，三次后通知管理员。

First establish whether three means total attempts or retries, who resubmits, and when notification occurs. **Only if the design has confirmed** a client with at most three retries after an initial failure, it could say:

> 首次校验失败后，客户端最多重新提交 3 次。任意一次校验成功后，客户端停止重试。
> 如果 3 次重试均校验失败，客户端通知管理员。

The clarification comes from a design decision, not from the editor's guess. If the counting rule is still open, state the alternatives and ask.

Distinguish required behavior from recommendations and possibilities using the repository's normative-language convention. Do not turn "may" or "planned" into "must" or "implemented". Do not add a new keyword scheme merely for consistency. Use steps for ordered operations, tables for genuine comparisons, and connected prose for explanations. Fixed sentence lengths and word substitutions do not establish clarity.

## Preserve decision history

Record important selections and their basis in the relevant template sections: the user's answer, an existing decision, or an explicitly delegated choice. Explain rejected alternatives sufficiently to make the choice reviewable. Link evidence near the claim it supports; a list of unread references is not research.

For revisions, preserve identifiers and history. Apply the local amendment or supersession procedure when meaning changes. Keep design acceptance, document merge, implementation, and release separate according to repository policy. Do not use a proposal's status as proof of running behavior.

## Check the result

Read the proposal as a reviewer who has not seen the conversation. Trace a representative input through the proposed behavior, including a boundary or failure case that could change the decision. The document should explain who acts, under which conditions, and what result would distinguish the proposal from the current behavior. An example that merely repeats the conclusion does not establish it.

Check consequential claims against their evidence and proposed guarantees against their acceptance criteria. For instance, "more reliable" needs a failure scenario and an expected result; it does not justify inventing a numerical target. Keep unsupported steps in the reasoning visible as gaps.

Run the repository's structural, link, and index checks. Inspect any generated or repaired diff and rerun the check. Passing a schema validates structure, not the design choice or its acceptance. Report remaining evidence and decision gaps alongside the checks actually performed.

Language checkers can flag wording for review. Assess a suggestion in context before applying it: removing an estimate, making examples an exhaustive list, or splitting a condition from its action can change the contract. Judge quality by whether the reader can make the intended decision with accurate information; fewer warnings or shorter sentences alone do not demonstrate an improvement.

## Writing references

- [ASD-STE100](https://asd-ste100.org/about_STE.html) describes controlled
  English for technical documentation.
- [Controlled technical Chinese](https://github.com/Fenng/Tech-Doc-Style-Chinese/blob/main/references/controlled-technical-chinese.md)
  illustrates adapting terminology consistency and semantic preservation to
  Chinese.
- [Simplified Technical Chinese](https://github.com/mzopedia/simplified-technical-chinese)
  supplies Chinese wording rules and a checker. Its
  [calibration report](https://github.com/mzopedia/simplified-technical-chinese/blob/main/docs/校准报告.md)
  distinguishes checker findings from evidence about reader comprehension.
- [Diátaxis](https://diataxis.fr/) organizes documentation around readers' needs.
  A proposal remains a decision record under local governance, with its own
  review questions and template.
- [Google Technical Writing](https://developers.google.com/tech-writing/one/clear-sentences)
  explains how specific subjects, verbs, and supported measurements improve
  technical explanations.

This guide uses those general editing ideas selectively. It does not reproduce the STE dictionary, apply English sentence limits to Chinese, or establish ASD-STE100 conformity.
