"""Deterministic attester: did the sanctioned SQL run exactly as written?

Takes an executor receipt (job_id, executed_sql, result) plus the contract's
computation text and parameter bindings; returns a verdict. No LLM involved —
the check is a mechanical comparison (OKF v0.2 §10.5): the SQL that actually
ran must equal the contract's computation with the declared parameters bound.
"""
from __future__ import annotations

import re


def _normalize(sql: str) -> str:
    """Collapse whitespace so formatting differences don't fail the check."""
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").lower()


def attest(receipt: dict, computation: str, parameters: dict) -> dict:
    """Return {ok, reason}. ``ok`` only when the bound computation ran."""
    expected = _normalize(computation)
    for name, value in parameters.items():
        expected = expected.replace(f"@{name}", repr(value).lower())
    ran = _normalize(receipt.get("executed_sql", ""))
    for name, value in parameters.items():
        ran = ran.replace(f"@{name}", repr(value).lower())
    if not receipt.get("job_id"):
        return {"ok": False, "reason": "receipt has no job_id"}
    if ran != expected:
        return {"ok": False, "reason": "executed_sql differs from the sanctioned computation"}
    return {"ok": True, "reason": f"job {receipt['job_id']} ran the sanctioned computation"}
