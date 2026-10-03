"""ZenDev's explicit allowed type/intention relation, separate from Gitmoji data."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

from zendev.message.gitmoji import Gitmoji, load_gitmojis


@dataclass(frozen=True, slots=True)
class IntentionPolicy:
    gitmoji: Gitmoji
    types: tuple[str, ...]
    breaking: bool = False


@dataclass(frozen=True, slots=True)
class MessagePolicy:
    types: tuple[str, ...]
    intentions: tuple[IntentionPolicy, ...]

    def for_type(self, name: str) -> tuple[IntentionPolicy, ...]:
        return tuple(item for item in self.intentions if name in item.types)

    def for_intention(self, name: str) -> IntentionPolicy:
        return next(item for item in self.intentions if item.gitmoji.name == name)


@cache
def load_policy() -> MessagePolicy:
    payload = tomllib.loads(files("zendev.message").joinpath("data/conventions.toml").read_text(encoding="utf-8"))
    types = payload["types"]
    intentions = payload["intentions"]
    breaking = payload["constraints"]["breaking"]
    catalog = load_gitmojis()
    names = {item.name for item in catalog}
    if (
        not isinstance(types, list)
        or not all(isinstance(name, str) for name in types)
        or len(set(types)) != len(types)
        or set(intentions) != names
        or not set(breaking) <= names
    ):
        raise ValueError("Message policy must classify the complete Gitmoji catalog with unique types")
    for name, allowed in intentions.items():
        if (
            not isinstance(allowed, list)
            or not allowed
            or len(set(allowed)) != len(allowed)
            or not set(allowed) <= set(types)
        ):
            raise ValueError(f"Invalid allowed types for intention {name}")
    return MessagePolicy(
        tuple(types),
        tuple(IntentionPolicy(item, tuple(intentions[item.name]), item.name in breaking) for item in catalog),
    )
