"""Attester: did the sanctioned SQL actually run? (OKF v0.2 §10.2)

Deterministic, no LLM. Re-derives the binding from the contract and compares it
against the SQL the server reports having executed. Illustrative sample code.
"""
from __future__ import annotations

import re


def normalize(sql: str) -> str:
    """Whitespace- and case-insensitive form; formatting is not a difference."""
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").lower()


def attest(computation: str, parameters: dict, receipt: dict) -> tuple[bool, str]:
    expected = computation
    for name, value in parameters.items():
        expected = expected.replace(f":{name}", repr(value))
    if normalize(expected) != normalize(receipt.get("executed_sql", "")):
        return False, "executed SQL is not the sanctioned computation bound with the claimed parameters"
    if not receipt.get("query_id"):
        return False, "receipt carries no query_id to re-read the result from"
    return True, "ok"
