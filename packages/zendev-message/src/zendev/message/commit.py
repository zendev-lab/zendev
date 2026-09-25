"""Pure message parsing, policy validation, and rendering."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from zendev.core.diagnostics import Diagnostic
from zendev.message.conventional import ConventionalCommit, ConventionalFooter, parse_conventional_commit
from zendev.message.gitmoji import Gitmoji, GitmojiCommit, load_gitmojis, match_gitmoji, parse_gitmoji_commit
from zendev.message.policy import load_policy


class MessageProfile(StrEnum):
    ZENDEV = "zendev"
    CONVENTIONAL = "conventional"
    GITMOJI = "gitmoji"


@dataclass(frozen=True, slots=True)
class ZendevCommit:
    commit: ConventionalCommit
    intention: Gitmoji
    token: str


ParsedMessage = ConventionalCommit | GitmojiCommit | ZendevCommit


@dataclass(frozen=True, slots=True)
class MessageResult:
    parsed: ParsedMessage | None
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.diagnostics


def _failure(code: str, message: str, *, hint: str | None = None) -> MessageResult:
    return MessageResult(None, (Diagnostic("message." + code, message, line=1, hint=hint),))


def parse_message(text: str, *, profile: MessageProfile | str = MessageProfile.ZENDEV) -> MessageResult:
    """Parse syntax only; policy checks are performed by check_message."""
    selected = MessageProfile(profile)
    if not text.strip():
        return _failure("empty", "The message is empty.")
    if selected is MessageProfile.CONVENTIONAL:
        parsed, issue = parse_conventional_commit(text)
    elif selected is MessageProfile.GITMOJI:
        parsed, issue = parse_gitmoji_commit(text)
    else:
        matched = match_gitmoji(text)
        if matched is None:
            return _failure(
                "missing-emoji",
                "Expected <emoji-or-shortcode> <type>(<scope>)!: <description>.",
                hint="Choose an intention explicitly; deps does not imply an upgrade.",
            )
        end = len(matched.token)
        if text[end : end + 1] != " " or text[end + 1 : end + 2].isspace():
            return _failure("separator", "Use exactly one space after the emoji or shortcode.")
        conventional, issue = parse_conventional_commit(matched.remainder)
        parsed = ZendevCommit(conventional, matched.gitmoji, matched.token) if conventional is not None else None
    if issue is not None:
        return MessageResult(None, (replace(issue, code="message." + issue.code),))
    return MessageResult(parsed)


def check_message(text: str, *, profile: MessageProfile | str = MessageProfile.ZENDEV) -> MessageResult:
    result = parse_message(text, profile=profile)
    parsed = result.parsed
    if not isinstance(parsed, ZendevCommit):
        return result
    policy = load_policy()
    name = parsed.commit.header.type
    intention = policy.for_intention(parsed.intention.name)
    if name not in policy.types:
        return _failure(
            "type",
            f"Unknown ZenDev type {name!r}.",
            hint="Allowed types: " + ", ".join(policy.types) + ". Dependency operations all use deps.",
        )
    if name not in intention.types:
        return _failure(
            "pair",
            f"{parsed.token} cannot be paired with {name!r}.",
            hint="Allowed types for this intention: " + ", ".join(intention.types),
        )
    if intention.breaking and not parsed.commit.is_breaking:
        return _failure("breaking", "This intention requires ! or a BREAKING CHANGE footer.")
    return result


def normalize_git_message(text: str, *, comment_char: str = "#") -> str:
    lines = []
    scissors = f"{comment_char} ------------------------ >8 ------------------------"
    for line in text.splitlines():
        if comment_char and line.startswith(scissors):
            break
        if comment_char and line.startswith(comment_char):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def check_git_message(
    text: str, *, profile: MessageProfile | str = MessageProfile.ZENDEV, comment_char: str = "#"
) -> MessageResult:
    normalized = normalize_git_message(text, comment_char=comment_char)
    if normalized.startswith(("Merge ", "Revert ", "fixup! ", "squash! ", "amend! ", "reword! ")):
        return MessageResult(None)
    return check_message(normalized, profile=profile)


@dataclass(frozen=True, slots=True)
class MessageDraft:
    subject: str
    type: str = ""
    intention: str | None = None
    scope: str = ""
    body: str = ""
    footers: tuple[ConventionalFooter, ...] = ()
    breaking: bool = False


def render_message(draft: MessageDraft, *, profile: MessageProfile | str = MessageProfile.ZENDEV) -> str:
    selected = MessageProfile(profile)
    if not draft.subject.strip() or any(c in draft.subject for c in "\r\n"):
        raise ValueError("Subject must be nonempty and single-line")
    if any(c in draft.scope for c in "()\r\n"):
        raise ValueError("Scope must be single-line and cannot contain parentheses")
    intention = next((item for item in load_gitmojis() if item.name == draft.intention), None)
    if selected is not MessageProfile.CONVENTIONAL and intention is None:
        raise ValueError("Choose an explicit Gitmoji intention")
    scope = f"({draft.scope})" if draft.scope else ""
    if selected is MessageProfile.GITMOJI:
        if draft.type or draft.breaking or draft.footers:
            raise ValueError("The gitmoji profile has no type or structured breaking/footer fields")
        assert intention is not None
        text = f"{intention.emoji} " + (scope + ": " if scope else "") + draft.subject
    else:
        if selected is MessageProfile.CONVENTIONAL and draft.intention is not None:
            raise ValueError("The conventional profile has no emoji intention")
        prefix = f"{intention.emoji} " if intention is not None else ""
        text = f"{prefix}{draft.type}{scope}{'!' if draft.breaking else ''}: {draft.subject}"
    if draft.body:
        text += "\n\n" + draft.body
    if draft.footers:
        text += "\n\n" + "\n".join(f"{footer.token}: {footer.value}" for footer in draft.footers)
    checked = check_message(text, profile=selected)
    if not checked.ok:
        raise ValueError(checked.diagnostics[0].message)
    parsed = checked.parsed.commit if isinstance(checked.parsed, ZendevCommit) else checked.parsed
    if isinstance(parsed, ConventionalCommit) and draft.footers != parsed.footers:
        raise ValueError("Footer token/value must preserve structured footers without becoming body text")
    return text
