"""Offline schema loading and introspection shared by checks and repairs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlsplit

from jsonschema import FormatChecker
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012

from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalToolError


def load_schema(config: ProposalConfig, path: Path):
    def read(path: Path) -> Any:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            validator_for(value).check_schema(value)

            if isinstance(value, dict) and "$schema" in value and cast(Any, validator_for)(value, default=None) is None:
                raise ValueError(f"unknown schema dialect: {value['$schema']}")

            def formats(node: object) -> None:
                if not isinstance(node, dict):
                    return
                if isinstance(node.get("format"), str) and node["format"] not in FormatChecker.checkers:
                    raise ValueError(f"unknown schema format: {node['format']}")
                for key in ("properties", "patternProperties", "dependentSchemas", "$defs", "definitions"):
                    for child in node.get(key, {}).values():
                        formats(child)
                for key in (
                    "items",
                    "contains",
                    "propertyNames",
                    "additionalProperties",
                    "unevaluatedProperties",
                    "unevaluatedItems",
                    "not",
                    "if",
                    "then",
                    "else",
                    "allOf",
                    "anyOf",
                    "oneOf",
                    "prefixItems",
                ):
                    child = node.get(key)
                    if isinstance(child, list):
                        for item in child:
                            formats(item)
                    else:
                        formats(child)

            formats(value)
            return value
        except (OSError, UnicodeError, ValueError, SchemaError, TypeError, AttributeError) as error:
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.schema.invalid",
                    path=config.relative_path(path),
                    message=f"cannot load schema: {error}",
                )
            ) from error

    def retrieve(uri: str):
        parsed = urlsplit(uri)
        if parsed.scheme != "file" or parsed.netloc:
            raise NoSuchResource(uri)
        local = Path(unquote(parsed.path)).resolve()
        if not local.is_relative_to(config.root) or local == config.index_path:
            raise NoSuchResource(uri)
        return Resource.from_contents(read(local), default_specification=DRAFT202012)

    schema = read(path)
    registry = cast(Any, Registry)(retrieve=retrieve).with_resource(
        path.as_uri(), Resource.from_contents(schema, default_specification=DRAFT202012)
    )
    validator = validator_for(schema)({"$ref": path.as_uri()}, registry=registry, format_checker=FormatChecker())
    return validator, schema, registry


def schema_properties(config: ProposalConfig, path: Path) -> dict[str, Any]:
    """Collect root properties across local references and schema alternatives."""
    _, schema, registry = load_schema(config, path)
    found: dict[str, Any] = {}
    visited: set[str] = set()

    def visit(node: Any, resolver: Any) -> None:
        if not isinstance(node, dict):
            return
        found.update(node.get("properties", {}))
        if "$ref" in node:
            key = str(node["$ref"])
            # Include resolver base in the key: sibling schemas may use the same pointer.
            signature = repr(resolver) + key
            if signature not in visited:
                visited.add(signature)
                resolved = resolver.lookup(key)
                visit(resolved.contents, resolved.resolver)
        for name in ("allOf", "anyOf", "oneOf"):
            for child in node.get(name, []):
                visit(child, resolver)

    try:
        visit(schema, registry.resolver(path.as_uri()))
    except (Unresolvable, RecursionError) as error:
        raise ProposalToolError(
            Diagnostic(code="proposal.schema.reference", path=config.relative_path(path), message=str(error))
        ) from error
    return found
