"""Core data models shared across engine modules."""

from __future__ import annotations

from typing import List


class Finding:
    def __init__(
        self,
        fid: str,
        severity: str,
        title: str,
        detail: str,
        evidence: List[str],
        category: str = "C3",
        recommended_fix: str = "",
        status: str = "open",
    ):
        self.id = fid
        self.severity = severity
        self.title = title
        self.detail = detail
        self.evidence = evidence
        self.category = category
        self.recommended_fix = recommended_fix
        self.status = status

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
            "finding": self.title,
            "plain_english_risk": self.detail,
            "evidence": self.evidence,
            "recommended_fix": self.recommended_fix,
            "status": self.status,
        }
