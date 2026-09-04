# streak round 2 — dsv4flash

**ADVERSARIAL REVIEW — STREAK ROUND 2**

**Scope of challenge:** I must find a way to make the "FULLY-GREEN" verdict false. I will attack each row family's *proof strength*, not just its existence.

---

**1. Fail-closed score trust boundary**

- **Claim:** "fail-closed" means any score computation error → non-green.
- **Attack:** Does the branch prove that *all* score inputs (not just the final aggregation) are validated? A classic paper-over is validating the *output* score (e.g., `if score < 0 → fail`) while allowing a *NaN* or *Infinity* to pass through an intermediate step that later gets clamped. If the chain only shows "score is a number" but not "every arithmetic operation is NaN/Inf-safe," then a `0/0` in a sub-weight could produce a `NaN` that fails a `>=` comparison → green. **Evidence gap:** The 101 tests must include a NaN/Inf propagation test through *every* weight path. If not, this is a false green.

**2. Full-keyword schema validation + report contract**

- **Claim:** schema validation rejects unknown/missing keywords.
- **Attack:** "Full-keyword" is meaningless unless the schema is *versioned* and the validator is *the same code* that the report generator uses. If the branch validates against a *stricter* schema than the generator emits, then a report that the generator produces could be rejected (false negative) — but that's not a false green. The dangerous direction: validator accepts a report that the *consumer* (e.g., a CI plugin) parses differently. **Evidence gap:** Is there a *round-trip* test: generate → validate → parse → re-generate → byte-identical? If not, the "contract" is only one-way.

**3. Scanner completeness + safe writes**

- **Claim:** scanner finds all defects; writes are atomic/safe.
- **Attack:** "Completeness" is unprovable for arbitrary code. The branch must define a *finite* defect taxonomy and prove coverage against *that* taxonomy. If the chain says "236 files zero findings" but the scanner's own test corpus only covers 20 defect types, then a 21st defect type (e.g., a new CWE) would be missed — but that's a *future* gap, not a current false green. **More dangerous:** "safe writes" — does the branch test *crash recovery* (kill -9 mid-write) and *permission-denied* paths? If the write is "safe" only under normal conditions, a partial write on disk-full could leave a corrupt state that *looks* green. **Evidence gap:** No crash-injection test in the listed evidence.

**4. Truthful backlog/diff semantics**

- **Claim:** backlog and diff are truthful.
- **Attack:** This is the easiest to fake. A "truthful diff" must be *bijective*: if the diff says file A changed, then file A *actually* changed, and *only* the listed changes occurred. If the branch uses a *content hash* but not a *line-level* diff, then a file with the same hash but different line endings (CRLF vs LF) would show as "unchanged" — a false green. **Evidence gap:** Are there tests for line-ending normalization, BOM, and trailing-whitespace-only changes? If not, the diff is not truthful.

**5. License aligned Apache-2.0 (file=badge)**

- **Claim:** license is Apache-2.0.
- **Attack:** A `LICENSE` file with the Apache-2.0 text is necessary but not sufficient. The branch must also ensure *no* dependency or vendored file has a conflicting license (e.g., GPL). The chain says "file=badge" — that only proves the file exists, not that the *entire* distribution is compliant. **Evidence gap:** Is there a license scanner (e.g., `license-checker`) run on all 236 files? If not, a GPL-licensed snippet in a vendored file would make the "Apache-2.0" claim false.

**6. Dogfood-defects**

- **Claim:** score-skeleton guidance, zero-byte redirect cure, eval/secret context suppression + tests.
- **Attack:** These are *specific* fixes. The "zero-byte redirect cure" — does it handle *all* redirect types (301, 302, 307, 308) and *relative* vs *absolute* URLs? If only 302 is tested, a 307 with a relative URL could still be a defect. **Evidence gap:** The test count (101) is suspiciously round. A production tool with 6 row families should have *more* than 101 tests if each family has edge cases. This suggests *shallow* coverage per family.

---

**Cross-cutting attack: The "101 tests + 53 subtests" count**

- **Attack:** Test *count* is not test *quality*. If the 101 tests are mostly happy-path and the 53 subtests are parameterized variations of the same 5 cases, then edge cases (NaN, crash, license conflict, line-ending diff) are untested. The chain says "deep CI scan 236 files zero findings" — but a *static* scan (e.g., grep for TODO) is not a *dynamic* proof of correctness.

**Most damning gap:** The chain does **not** mention a single *negative* test that *proves* the tool fails when it should. A fail-closed tool must have tests that assert "this input → non-green" for *every* failure mode. If the 101 tests are all positive (green→green), then the fail-closed claim is unproven.

---

**Verdict reasoning:**

- The evidence proves the branch *exists* and *passes its own tests*.
- It does **not** prove: NaN/Inf safety across all weight paths, round-trip report contract, crash-recovery writes, line-ending diff truthfulness, full-distribution license compliance, or negative-path test coverage.
- Any one of these gaps could make the green *false* in production.

**FULLY-GREEN: no** — the chain proves *internal consistency* but not *production truthfulness*; missing negative-path tests, crash-injection, and license-scanner evidence make the green unproven.