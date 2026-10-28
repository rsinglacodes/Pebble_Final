"""Tests for DSA keywords simple plurals matching and non-matching."""

import pytest
from backend.app.core.dsa_keywords import contains_dsa_keyword


@pytest.mark.parametrize(
    "phrase",
    [
        "strings",
        "graphs",
        "arrays",
        "trees",
        "linked lists",
    ],
)
def test_dsa_keywords_plurals_match(phrase: str):
    """Ensure simple plurals and pluralized multi-word keywords match DSA keywords."""
    assert contains_dsa_keyword(phrase) is True


@pytest.mark.parametrize(
    "phrase",
    [
        "tell me a joke",
        "I am on holiday",
    ],
)
def test_non_dsa_keywords_do_not_match(phrase: str):
    """Ensure off-topic and unrelated text do not match DSA keywords."""
    assert contains_dsa_keyword(phrase) is False
