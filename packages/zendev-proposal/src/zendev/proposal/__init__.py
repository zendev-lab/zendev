"""Repository-native proposal validation and indexing."""

from zendev.proposal.application import ChangePlan, apply_plan, check_project, plan_changes
from zendev.proposal.config import load_config
from zendev.proposal.indexing import build_index, expected_index_text
from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalDocument
from zendev.proposal.validation import validate_repository

__all__ = [
    "ChangePlan",
    "Diagnostic",
    "ProposalConfig",
    "ProposalDocument",
    "apply_plan",
    "build_index",
    "check_project",
    "expected_index_text",
    "load_config",
    "plan_changes",
    "validate_repository",
]
