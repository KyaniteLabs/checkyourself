# ROLE: CORRECTNESS HUNTER (luna @ max) — checkyourself stage-1
Read _retrofit-2026-09-04/FACTS.md first; it is authoritative.
Your lens: CODE-LEVEL DEFECTS, exhaustively. Hunt in tools/*.py, schemas/, tests/, Dockerfile, 06_ADAPTERS/:
- Logic bugs, off-by-one, inverted conditions, wrong exception handling, silent failures, unreachable branches, type errors, encoding/path bugs (spaces, unicode), platform assumptions.
- Every finding: file:line + verbatim code snippet + concrete failure scenario ("input X → wrong output Y").
- Run the deterministic pipeline end-to-end on samples/ or a scratch copy INSIDE _retrofit-2026-09-04/ (you may create scratch files there only) — record actual outputs vs expected.
- Do NOT report style nits; defects only. Do not modify anything outside _retrofit-2026-09-04/.
Output ONLY: _retrofit-2026-09-04/FINDINGS-luna-a.md (FACTS output contract).
