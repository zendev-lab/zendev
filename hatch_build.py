"""Pin sibling distributions to the version resolved by Hatch VCS."""

from typing import Any

from hatchling.metadata.plugin.interface import MetadataHookInterface


class SiblingDependencies(MetadataHookInterface):
    def update(self, metadata: dict[str, Any]) -> None:
        metadata["dependencies"] = [
            requirement.format(version=metadata["version"]) for requirement in self.config["dependencies"]
        ]
