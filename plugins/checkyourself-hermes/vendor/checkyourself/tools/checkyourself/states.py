"""Named lifecycles for coverage and finding statuses.

CheckYourself persists two status vocabularies as plain strings in JSON
artifacts.  This module is the one place that names them, lists their legal
moves, and refuses illegal ones.  Stored values are unchanged: every member's
``.value`` is the exact string already on disk.

1. Coverage status (per surface, then folded per score category)

   A reviewer *declares* a surface status; the evidence gate derives the
   *effective* status the score is allowed to trust::

       declared                    gate                         effective
       --------                    ----                         ---------
       Pass           --verified evidence_reviewed-------------> Pass
       Pass           --otherwise-------------------------------> Unknown
       NotApplicable  --reason + verified delegation receipt----> NotApplicable
       NotApplicable  --otherwise-------------------------------> Unknown
       Finding        ------------------------------------------> Finding
       Unknown        ------------------------------------------> Unknown
       <missing/unrecognized> (tolerant legacy read) -----------> Unknown

   A score category folds its surfaces' effective statuses, worst wins::

       MissingCoverage (no rows) < NotApplicable < Pass < Unknown < Finding

   ``MissingCoverage`` is category-only; a surface may never declare it.

2. Finding status (workflow disposition)

   ::

       open ----resolve (reviewed not-applicable)---> not-applicable  [terminal]
         +---suppress (reviewed suppression)----> suppressed
       suppressed / deferred / accepted-risk ---resolve / suppress---> (as above)
       fixed  (human-set)                                             [terminal]

   ``fixed`` and ``not-applicable`` are the only statuses that close the
   underlying risk.  Unrecognized legacy strings read as unresolved.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Optional


class CoverageStatus(str, Enum):
    PASS = "Pass"
    FINDING = "Finding"
    UNKNOWN = "Unknown"
    NOT_APPLICABLE = "NotApplicable"
    MISSING_COVERAGE = "MissingCoverage"


# Statuses a reviewer may write on a coverage surface row.
DECLARABLE_COVERAGE_STATUSES = frozenset(
    {
        CoverageStatus.PASS.value,
        CoverageStatus.FINDING.value,
        CoverageStatus.UNKNOWN.value,
        CoverageStatus.NOT_APPLICABLE.value,
    }
)

# Declared statuses that are claims and therefore need verifier evidence.
EVIDENCE_GATED_COVERAGE_STATUSES = frozenset({CoverageStatus.PASS, CoverageStatus.NOT_APPLICABLE})

# Category fold order: a higher rank is a worse (more conservative) state.
COVERAGE_STATUS_RANK = {
    CoverageStatus.MISSING_COVERAGE: 0,
    CoverageStatus.NOT_APPLICABLE: 1,
    CoverageStatus.PASS: 2,
    CoverageStatus.UNKNOWN: 3,
    CoverageStatus.FINDING: 4,
}


def parse_declared_coverage_status(raw: Any) -> Optional[CoverageStatus]:
    """Return the declared surface status, or ``None`` when it is not legal."""
    if isinstance(raw, str) and raw in DECLARABLE_COVERAGE_STATUSES:
        return CoverageStatus(raw)
    return None


def has_not_applicable_reason(item: Mapping[str, Any]) -> bool:
    """The single definition of a usable ``not_applicable_reason``."""
    return bool(str(item.get("not_applicable_reason") or "").strip())


def gate_surface_status(
    declared: Any,
    *,
    verified_evidence: bool,
    verified_delegation: bool,
    not_applicable_reason: bool,
) -> CoverageStatus:
    """Derive the effective surface status from the declared one.

    This is the only place a claim is demoted to ``Unknown``.  Anything that is
    not a legal declared status reads as ``Unknown`` so a typo can never earn
    credit.
    """
    status = parse_declared_coverage_status(declared)
    if status is CoverageStatus.PASS:
        return CoverageStatus.PASS if verified_evidence else CoverageStatus.UNKNOWN
    if status is CoverageStatus.NOT_APPLICABLE:
        if verified_delegation and not_applicable_reason:
            return CoverageStatus.NOT_APPLICABLE
        return CoverageStatus.UNKNOWN
    if status is None:
        return CoverageStatus.UNKNOWN
    return status


def fold_category_status(current: Optional[Any], incoming: Any) -> CoverageStatus:
    """Fold one more effective surface status into a category, worst wins."""
    new = CoverageStatus(incoming)
    if new is CoverageStatus.MISSING_COVERAGE:
        raise ValueError("MissingCoverage is derived for empty categories, never folded from a surface")
    if current is None:
        return new
    old = CoverageStatus(current)
    return new if COVERAGE_STATUS_RANK[new] > COVERAGE_STATUS_RANK[old] else old


def finalize_category_status(current: Optional[Any]) -> CoverageStatus:
    """Close a category fold: no surfaces at all means ``MissingCoverage``."""
    return CoverageStatus.MISSING_COVERAGE if current is None else CoverageStatus(current)


def category_needs_evidence(state: Mapping[str, Any]) -> bool:
    """True when a category cannot be trusted without more evidence.

    Used by every reader (manual-evidence list, critical and high-score caps,
    confidence) so they cannot disagree about what counts as a gap.
    """
    return bool(state.get("has_unknown")) or state.get("status") in {
        CoverageStatus.UNKNOWN.value,
        CoverageStatus.MISSING_COVERAGE.value,
    }


class FindingStatus(str, Enum):
    OPEN = "open"
    FIXED = "fixed"
    ACCEPTED_RISK = "accepted-risk"
    DEFERRED = "deferred"
    NOT_APPLICABLE = "not-applicable"
    SUPPRESSED = "suppressed"


WORKFLOW_DISPOSITIONS = frozenset(status.value for status in FindingStatus if status is not FindingStatus.OPEN)
RESOLVED_STATUSES = frozenset({FindingStatus.FIXED.value, FindingStatus.NOT_APPLICABLE.value})

# Engine-written moves, each from any unresolved status (including
# unrecognized legacy strings) to one target.  Resolved statuses are terminal.
# ``fixed``, ``deferred`` and ``accepted-risk`` are human dispositions read
# from artifacts; the engine never writes them.
FINDING_TRANSITIONS = {
    "resolve": FindingStatus.NOT_APPLICABLE,
    "suppress": FindingStatus.SUPPRESSED,
}


class IllegalTransition(ValueError):
    """Raised when a status move is not in the named lifecycle."""


def finding_status(finding: Mapping[str, Any]) -> str:
    """Read a finding's stored status; missing or empty means ``open``.

    Unrecognized legacy strings are returned verbatim (and stay unresolved).
    """
    return str(finding.get("status") or FindingStatus.OPEN.value)


def is_resolved_status(status: Any) -> bool:
    """Return True only for dispositions that close the underlying risk.

    This is the single definition of "no longer counts" used by scan counts,
    scoring, diff, backlog, next, report rendering, and the CI gate.  A
    workflow label such as ``suppressed``, ``accepted-risk`` or ``deferred``
    keeps the finding unresolved until the exposure is fixed or proven not
    applicable.
    """
    return str(status or FindingStatus.OPEN.value) in RESOLVED_STATUSES


def can_transition_finding(finding: Mapping[str, Any], move: str) -> bool:
    return move in FINDING_TRANSITIONS and not is_resolved_status(finding_status(finding))


def transition_finding(finding: dict, move: str) -> dict:
    """Apply one named move to a finding dict in place, refusing illegal moves."""
    if move not in FINDING_TRANSITIONS:
        raise IllegalTransition(f"unknown finding transition: {move!r}")
    target = FINDING_TRANSITIONS[move]
    if not can_transition_finding(finding, move):
        raise IllegalTransition(f"cannot {move} finding in status {finding_status(finding)!r}")
    finding["status"] = target.value
    return finding
