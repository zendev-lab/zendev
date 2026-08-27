"""Type-check the public APIs as an installed complete-toolkit consumer."""

from typing import assert_type

from zendev.body import BodySection, validate_body
from zendev.commit import CommitProfile, ValidationResult, validate_commit_message
from zendev.log import setup_log
from zendev.proposal import ProposalConfig, load_config

assert_type(validate_commit_message("✨ feat: add export", profile=CommitProfile.ZENDEV), ValidationResult)
assert_type(validate_body("## Summary\n", [BodySection("Summary")]), tuple[bool, list[str]])
assert_type(setup_log(), int | None)
assert_type(load_config(), ProposalConfig)
