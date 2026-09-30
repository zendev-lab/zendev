"""Pin sibling distributions to the version resolved from SCM."""

from pdm.backend.hooks import Context


def pdm_build_hook_enabled(context: Context) -> bool:
    # Sdists record the resolved pins as static dependencies.
    return "dependencies" in context.config.metadata.get("dynamic", [])


def pdm_build_initialize(context: Context) -> None:
    metadata = context.config.metadata
    metadata["dependencies"] = [
        requirement.format(version=metadata["version"])
        for requirement in context.config.data["tool"]["zendev-build"]["dependencies"]
    ]
    metadata["dynamic"].remove("dependencies")
    if context.target == "sdist":
        # Component hooks live at the repository root, outside the sdist.
        context.config.build_config.pop("custom-hook", None)
