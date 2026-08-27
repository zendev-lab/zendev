"""Repository-native proposal validation and indexing."""

from zendev.proposal.config import load_config
from zendev.proposal.indexing import build_index, expected_index_text
from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalDocument
from zendev.proposal.validation import validate_repository

__all__ = [
    "Diagnostic",
    "ProposalConfig",
    "ProposalDocument",
    "build_index",
    "expected_index_text",
    "load_config",
    "validate_repository",
]
