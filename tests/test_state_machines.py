"""Tests for the named coverage and finding lifecycles in ``states.py``.

Every table here is keyed by the full enum so adding a state without deciding
its behavior fails a test.
"""

from __future__ import annotations

import random
import unittest
from unittest import mock

from tools.checkyourself import coverage as coverage_mod
from tools.checkyourself import scoring
from tools.checkyourself.config import apply_resolutions, apply_suppressions
from tools.checkyourself.constants import (
    COVERAGE_SCHEMA_ID,
    COVERAGE_SURFACES,
    RESOLVED_STATUSES,
    VALID_COVERAGE_STATUSES,
    WORKFLOW_DISPOSITIONS,
)
from tools.checkyourself.states import (
    COVERAGE_STATUS_RANK,
    DECLARABLE_COVERAGE_STATUSES,
    FINDING_TRANSITIONS,
    CoverageStatus,
    FindingStatus,
    IllegalTransition,
    can_transition_finding,
    category_needs_evidence,
    finalize_category_status,
    finding_status,
    fold_category_status,
    gate_surface_status,
    is_resolved_status,
    parse_declared_coverage_status,
    transition_finding,
)

C = CoverageStatus
F = FindingStatus

# Persisted strings must never change: these are the bytes already on disk.
COVERAGE_WIRE = {
    C.PASS: "Pass",
    C.FINDING: "Finding",
    C.UNKNOWN: "Unknown",
    C.NOT_APPLICABLE: "NotApplicable",
    C.MISSING_COVERAGE: "MissingCoverage",
}
FINDING_WIRE = {
    F.OPEN: "open",
    F.FIXED: "fixed",
    F.ACCEPTED_RISK: "accepted-risk",
    F.DEFERRED: "deferred",
    F.NOT_APPLICABLE: "not-applicable",
    F.SUPPRESSED: "suppressed",
}

# declared -> (all evidence present, nothing present)
GATE_TABLE = {
    C.PASS: (C.PASS, C.UNKNOWN),
    C.FINDING: (C.FINDING, C.FINDING),
    C.UNKNOWN: (C.UNKNOWN, C.UNKNOWN),
    C.NOT_APPLICABLE: (C.NOT_APPLICABLE, C.UNKNOWN),
    C.MISSING_COVERAGE: (C.UNKNOWN, C.UNKNOWN),  # category-only: never declarable
}

NEEDS_EVIDENCE = {
    C.PASS: False,
    C.FINDING: False,
    C.UNKNOWN: True,
    C.NOT_APPLICABLE: False,
    C.MISSING_COVERAGE: True,
}

# (status, move) -> resulting status, or None when the move is illegal.
FINDING_TABLE = {
    (F.OPEN, "resolve"): F.NOT_APPLICABLE,
    (F.OPEN, "suppress"): F.SUPPRESSED,
    (F.SUPPRESSED, "resolve"): F.NOT_APPLICABLE,
    (F.SUPPRESSED, "suppress"): F.SUPPRESSED,
    (F.DEFERRED, "resolve"): F.NOT_APPLICABLE,
    (F.DEFERRED, "suppress"): F.SUPPRESSED,
    (F.ACCEPTED_RISK, "resolve"): F.NOT_APPLICABLE,
    (F.ACCEPTED_RISK, "suppress"): F.SUPPRESSED,
    (F.FIXED, "resolve"): None,
    (F.FIXED, "suppress"): None,
    (F.NOT_APPLICABLE, "resolve"): None,
    (F.NOT_APPLICABLE, "suppress"): None,
}


class CoverageStateMachineTests(unittest.TestCase):
    def test_tables_are_exhaustive_over_the_enum(self) -> None:
        for table in (COVERAGE_WIRE, GATE_TABLE, NEEDS_EVIDENCE, COVERAGE_STATUS_RANK):
            self.assertEqual(set(table), set(CoverageStatus))

    def test_persisted_values_are_unchanged(self) -> None:
        for member, wire in COVERAGE_WIRE.items():
            self.assertEqual(member.value, wire)
        self.assertEqual(VALID_COVERAGE_STATUSES, {"Pass", "Finding", "Unknown", "NotApplicable"})
        self.assertEqual(set(DECLARABLE_COVERAGE_STATUSES), VALID_COVERAGE_STATUSES)

    def test_gate_table(self) -> None:
        for declared, (with_evidence, without_evidence) in GATE_TABLE.items():
            with self.subTest(declared=declared):
                full = gate_surface_status(
                    declared.value, verified_evidence=True, verified_delegation=True, not_applicable_reason=True
                )
                empty = gate_surface_status(
                    declared.value, verified_evidence=False, verified_delegation=False, not_applicable_reason=False
                )
                self.assertIs(full, with_evidence)
                self.assertIs(empty, without_evidence)

    def test_not_applicable_needs_both_reason_and_delegation(self) -> None:
        for delegation, reason in ((True, False), (False, True)):
            status = gate_surface_status(
                "NotApplicable", verified_evidence=True, verified_delegation=delegation, not_applicable_reason=reason
            )
            self.assertIs(status, C.UNKNOWN)

    def test_legacy_and_garbage_declared_values_read_as_unknown(self) -> None:
        for raw in (None, "", "pass", "Passed", "PASS", "N/A", 1, ["Pass"]):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_declared_coverage_status(raw))
                self.assertIs(
                    gate_surface_status(
                        raw, verified_evidence=True, verified_delegation=True, not_applicable_reason=True
                    ),
                    C.UNKNOWN,
                )

    def test_fold_is_worst_wins_and_refuses_missing_coverage(self) -> None:
        surface_states = [s for s in CoverageStatus if s is not C.MISSING_COVERAGE]
        for a in surface_states:
            for b in surface_states:
                folded = fold_category_status(fold_category_status(None, a), b)
                self.assertIs(folded, max(a, b, key=COVERAGE_STATUS_RANK.__getitem__))
        with self.assertRaises(ValueError):
            fold_category_status(None, C.MISSING_COVERAGE)
        self.assertIs(finalize_category_status(None), C.MISSING_COVERAGE)
        self.assertIs(finalize_category_status("Pass"), C.PASS)

    def test_fold_property_order_independent(self) -> None:
        rng = random.Random(20261110)
        surface_states = [s for s in CoverageStatus if s is not C.MISSING_COVERAGE]
        for _ in range(500):
            seq = [rng.choice(surface_states) for _ in range(rng.randint(1, 8))]
            current = None
            for step in seq:
                previous = current
                current = fold_category_status(current, step)
                # Invariant after every step: never better than any input so far.
                if previous is not None:
                    self.assertGreaterEqual(COVERAGE_STATUS_RANK[current], COVERAGE_STATUS_RANK[previous])
            shuffled = list(seq)
            rng.shuffle(shuffled)
            other = None
            for step in shuffled:
                other = fold_category_status(other, step)
            self.assertIs(current, other)

    def test_needs_evidence_table(self) -> None:
        for status, expected in NEEDS_EVIDENCE.items():
            self.assertEqual(category_needs_evidence({"status": status.value}), expected, status)
            self.assertTrue(category_needs_evidence({"status": status.value, "has_unknown": True}))


def _all_not_applicable_coverage(reason: str) -> dict:
    return {
        "schema": COVERAGE_SCHEMA_ID,
        "surfaces": [
            {
                "id": sid,
                "surface": surface,
                "category": category,
                "status": "NotApplicable",
                "evidence_reviewed": [],
                "not_applicable_reason": reason,
                "delegation_receipts": [{"reference": f"{sid}.txt"}],
            }
            for sid, surface, category in COVERAGE_SURFACES
        ],
    }


class CoverageBugRegressionTests(unittest.TestCase):
    def test_check_and_score_agree_on_blank_not_applicable_reason(self) -> None:
        """Bug: ``coverage --check`` used a truthy test and accepted "   " as a
        reason (complete=True) while ``score`` stripped it and demoted the row,
        so the two receipts disagreed about the same artifact."""
        coverage = _all_not_applicable_coverage("   ")
        verified = mock.patch.object(coverage_mod, "_verify_receipts", return_value=(["ok"], []))
        with verified:
            check = coverage_mod.coverage_check(coverage)
            score = scoring.score_from_inputs({"findings": []}, coverage)
        self.assertFalse(check["complete"])
        self.assertTrue(any("not_applicable_reason" in error for error in check["errors"]))
        self.assertFalse(score["coverage_complete"])
        self.assertEqual(check["complete"], score["coverage_complete"])

    def test_check_and_score_agree_when_reason_is_present(self) -> None:
        coverage = _all_not_applicable_coverage("No such surface in this project.")
        with mock.patch.object(coverage_mod, "_verify_receipts", return_value=(["ok"], [])):
            check = coverage_mod.coverage_check(coverage)
            score = scoring.score_from_inputs({"findings": []}, coverage)
        self.assertTrue(check["complete"], check)
        self.assertTrue(score["coverage_complete"])

    def test_unrecognized_coverage_status_never_earns_credit(self) -> None:
        """Bug: ``category_coverage`` folded an unrecognized status such as
        "Passed" into the category as-is, without marking it Unknown, so the
        category scored as if it had full evidence."""
        sid, surface, category = next(row for row in COVERAGE_SURFACES if row[2] == "C1")
        data = {
            "schema": COVERAGE_SCHEMA_ID,
            "surfaces": [{"id": sid, "surface": surface, "category": category, "status": "Passed"}],
        }
        by_category, _complete = scoring.category_coverage(data, None)
        state = by_category[category]
        self.assertEqual(state["status"], "Unknown")
        self.assertTrue(state["has_unknown"])
        self.assertTrue(any("unrecognized status" in item for item in state["missing_evidence"]))

    def test_scan_estimate_lists_every_unknown_category_as_needing_evidence(self) -> None:
        """Bug: the "needs evidence" predicate was copy-pasted four times and
        three copies ignored a plain ``Unknown`` status, so scan-derived C3/C5/C6
        were Unknown yet missing from ``manual_evidence_needed``."""
        scan_data = {"schema": "checkyourself-scan/1", "findings": [], "tests": ["tests/x.py"], "ci": ["ci.yml"]}
        result = scoring.score_from_inputs(scan_data)
        needed = {item["category"] for item in result["manual_evidence_needed"]}
        unknown = {item["id"] for item in result["per_category"] if item["coverage_status"] == "Unknown"}
        self.assertTrue({"C3", "C5", "C6"} <= unknown)
        self.assertTrue(unknown <= needed, (unknown, needed))


class FindingStateMachineTests(unittest.TestCase):
    def test_tables_are_exhaustive_over_the_enum(self) -> None:
        self.assertEqual(set(FINDING_WIRE), set(FindingStatus))
        self.assertEqual({key for key in FINDING_TABLE}, {(s, m) for s in FindingStatus for m in FINDING_TRANSITIONS})

    def test_persisted_values_are_unchanged(self) -> None:
        for member, wire in FINDING_WIRE.items():
            self.assertEqual(member.value, wire)
        self.assertEqual(WORKFLOW_DISPOSITIONS, {"fixed", "accepted-risk", "deferred", "not-applicable", "suppressed"})
        self.assertEqual(RESOLVED_STATUSES, {"fixed", "not-applicable"})

    def test_transition_table(self) -> None:
        for (status, move), expected in FINDING_TABLE.items():
            with self.subTest(status=status, move=move):
                finding = {"id": "F", "status": status.value}
                if expected is None:
                    self.assertFalse(can_transition_finding(finding, move))
                    with self.assertRaises(IllegalTransition):
                        transition_finding(finding, move)
                    self.assertEqual(finding["status"], status.value)
                else:
                    self.assertTrue(can_transition_finding(finding, move))
                    transition_finding(finding, move)
                    self.assertEqual(finding["status"], expected.value)

    def test_unknown_move_is_refused(self) -> None:
        with self.assertRaises(IllegalTransition):
            transition_finding({"status": "open"}, "fix")

    def test_legacy_status_reads(self) -> None:
        self.assertEqual(finding_status({}), "open")
        self.assertEqual(finding_status({"status": None}), "open")
        self.assertEqual(finding_status({"status": ""}), "open")
        self.assertEqual(finding_status({"status": "wontfix"}), "wontfix")
        self.assertFalse(is_resolved_status("wontfix"))
        # A legacy unresolved string can still be resolved by a reviewed entry.
        legacy = {"status": "wontfix"}
        transition_finding(legacy, "resolve")
        self.assertEqual(legacy["status"], "not-applicable")

    def test_random_walk_invariants(self) -> None:
        rng = random.Random(1110)
        starts = [s.value for s in FindingStatus] + ["wontfix", None]
        moves = sorted(FINDING_TRANSITIONS)
        for _ in range(300):
            finding = {"status": rng.choice(starts)}
            for _step in range(rng.randint(1, 10)):
                before = finding_status(finding)
                move = rng.choice(moves)
                if is_resolved_status(before):
                    with self.assertRaises(IllegalTransition):
                        transition_finding(finding, move)
                    self.assertEqual(finding_status(finding), before)
                else:
                    transition_finding(finding, move)
                    self.assertEqual(finding["status"], FINDING_TRANSITIONS[move].value)
                # Invariants after every step.
                if is_resolved_status(before):
                    self.assertTrue(is_resolved_status(finding_status(finding)))
                self.assertTrue(
                    finding_status(finding) in FINDING_WIRE.values() or finding_status(finding) == "wontfix"
                )

    def test_resolutions_leave_terminal_findings_alone(self) -> None:
        fixed = {"id": "CY-X", "status": "fixed", "evidence": ["a.py:1"]}
        opened = {"id": "CY-X", "status": "open", "evidence": ["a.py:1"]}
        apply_resolutions([fixed, opened], [{"id": "CY-X", "reason": "n/a", "files": []}])
        self.assertEqual(fixed["status"], "fixed")
        self.assertNotIn("disposition", fixed)
        self.assertEqual(opened["status"], "not-applicable")

    def test_resolution_wins_over_suppression(self) -> None:
        finding = {"id": "CY-X", "status": "open", "evidence": ["a.py:1"]}
        apply_resolutions([finding], [{"id": "CY-X", "reason": "n/a", "files": []}])
        apply_suppressions([finding], [{"id": "CY-X", "reason": "noise"}])
        self.assertEqual(finding["status"], "not-applicable")
        self.assertNotIn("suppression", finding)


if __name__ == "__main__":
    unittest.main()
