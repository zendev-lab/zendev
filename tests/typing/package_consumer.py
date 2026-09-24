"""Type-check the public APIs as an installed complete-toolkit consumer."""

from typing import assert_type

from zendev.core.diagnostics import Diagnostic
from zendev.log import setup_log
from zendev.message import MessageProfile, MessageResult, check_message
from zendev.message.body import check_body
from zendev.proposal import ProposalConfig, load_config

assert_type(check_message("✨ feat: add export", profile=MessageProfile.ZENDEV), MessageResult)
assert_type(check_body("## Summary\n", "## Summary\n"), tuple[Diagnostic, ...])
assert_type(setup_log(), int | None)
assert_type(load_config(), ProposalConfig)
