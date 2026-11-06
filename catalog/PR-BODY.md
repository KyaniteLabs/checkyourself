Disclosure — scoring re-executes the operator-approved project's challenge commands. Those commands can read/write files, use network services and incur their own costs. There is no fixed remote destination or telemetry, and no model/API call in the plugin. MCP receives only CHECKYOURSELF_SCAN_ROOT and PYTHONDONTWRITEBYTECODE, not inherited credentials. Project code still has OS authority: this is NOT a sandbox. Challenge issuance writes local captures/receipts/integrity state; verification reads these, the project and its local integrity key, and reruns commands. Enable only after inspecting/approving the challenge configuration with CHECKYOURSELF_ALLOW_CHALLENGES=1. No bundled binaries, runtime self-update or credential-store reads.

## Native value
A hard pre_tool_call gate refuses kanban_complete without verified S11 executed-test evidence. Incomplete claims and tampered captures block; adding real executed evidence allows completion. The same upstream MCP engine scores both the native tool and hook. This is not merely an MCP listing.

Scope is deliberately bounded: C5 test-evidence policy, not all production surfaces; claim text is a label, not independent semantic proof. Does not intercept prose answers, external board clients or review handoffs. Complements hermes-verifier/agent-run-debugger rather than claiming their diagnostic coverage.

## Exact provenance and proof
- Product repository KyaniteLabs/checkyourself; source-only plugin subdir hermes-plugin at 30f77352cc3a28b2341af9f8a8c8d928be487d0f.
- Engine snapshot b2a5684bf9e5232f2c945060dbac8a76c0517d6a, 42 files byte-checked with tools/build_hermes_plugin.py. Shared scaffold b0ff57e17ffd2403647e8bdc87c928b0805bb6f3.
- Tested Hermes runtime e76fbd80be65ea5c1b89831f8d7aaedb713f5cac; manifest/catalog floor >=0.23.0. Linux verified; macOS unverified; Windows unsupported.
- Real validator: ok=true, 15 checks, zero warnings. Full suite: 162 tests, one runtime integration skipped there and run separately (passed). Real native discovery + registered tool + hook dispatch + stdio MCP demonstrated incomplete score29/block → executed C5 credit/allow (overall production score34) → capture tamper/block. Sequence 1.246 seconds; final DONE is a labeled simulated sink, not a real board mutation.
- Product exact-head CI/review/merge links must be taken from the product PR at submission; local receipts do not imply hosted CI or approval. Simon checks these gates Nov 9 before opening the catalog PR Nov 11.
- Demo recording/captions and optional 2:1 banner/screenshots are capture work, not claimed attached. Script: demo/90-seconds.md. Omit optional image fields until real media exists.

## Safety / rollback
Import/register are pure registration. Public ctx APIs only. No new runtime dependencies. Pytest 8.3.5 is CI/demo-only, a long-established release. Config is process-scoped: use separate launch processes for different roots/profiles. Completion fails closed on absent opt-in/root/artifacts, stale source/config, tamper, MCP errors/timeouts. MCP child group is bounded to 20 seconds; set Hermes hook budget to 25 seconds. Rollback: disable/remove the plugin; no board schema or history changes. No production activation performed.

Submission is from Simon's personal fork on Nov 11; this file is a prepared body, NOT an opened catalog PR.
