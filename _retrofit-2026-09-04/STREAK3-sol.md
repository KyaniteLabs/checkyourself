# SOL independent review — streak round 3

Status: DONE

Fresh acceptance is green.

- `python3 -m pytest tests/ -q`: 113 passed, 86 subtests passed in 66.33s.
- `python3 tools/validate_public.py .`: passed with `OK: public CheckYourself validation passed`.

## False-green review

No false green reproduced.

- Report proof is behavioral: `regenerate_report` validates the real report schema, emits canonical JSON with `allow_nan=False`, `parse_report` uses the strict production parser and the same schema, and the test proves parse/regenerate byte stability. The score/backlog-to-report test executes both CLI producers, validates their assembled report through the public CLI contract, and rejects invalid mutations.
- JSON edge proof is behavioral: the production loader strips only a leading UTF-8 BOM, rejects `NaN` and explicit infinities through `parse_constant`, rejects overflow such as `1e309` through the recursive finite-number guard, and accepts trailing JSON whitespace. The diff test executes these paths and still detects a real newly-open P1 regression.
- Write-failure proof is behavioral: subprocess tests reach real `SIGKILL` termination at the replace boundary and real directory-mode permission denial. Fault injection reaches `fsync` and `replace`, verifies the prior destination survives, and verifies ordinary exception cleanup. Corrupt-history recovery allows the real backup rename, kills the subsequent replace, and verifies the corrupt receipt remains preserved in the backup.
- The five prior DSV4 gap classes remain covered: non-finite arithmetic/input rejection, malformed and corrupt receipt failure, truncated coverage fail-closed behavior, report contract round-trip/rejection, and semantic line-ending/BOM diff behavior. The full suite and public validator found no regression.

## Concern

The permission-denial proof is platform-sensitive and skips under root because root bypasses mode bits. It ran in this non-root review. This is a portability limitation, not a false green in the reviewed environment.

## IMPROVEMENTS

1. Add a portable non-root CI lane for the permission test. WHY: privileged runners skip the only real mode-bit denial receipt. FIX: execute that focused test after a supported privilege drop or in an explicitly non-root job.
2. Add a documented report-normalize CLI command. WHY: parser/regenerator correctness is currently exposed only through the Python module boundary. FIX: wrap `parse_report` and `regenerate_report` in a read-only/stdout command and exercise the same round trip through the public interface.

FULLY-GREEN: yes
