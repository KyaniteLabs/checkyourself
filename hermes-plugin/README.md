# Check Yourself Evidence Gate

**Disclosure first:** enabling this plugin can run commands from the operator's project `.checkyourself/challenges.json` during evidence scoring, including at a completion attempt. Those commands can read/write files, contact the network, and incur whatever costs the operator's commands cause. This is not a sandbox or an approval bypass. Review and approve the challenge configuration before setting `CHECKYOURSELF_ALLOW_CHALLENGES=1`. Never enable it on an untrusted project. No automatic opt-in, credential access, model calls, telemetry, self-updates, bundled binaries, or background daemon. The MCP child gets a scrubbed environment; project commands run with the process's OS authority, not filesystem confinement. The engine reads the project and its local integrity-binding key; that key is local receipt integrity, not a remote credential. Challenge issuance writes captures, receipts and integrity state under `.checkyourself/`; challenge verification re-executes commands and may create caches. Do not use tests that require production credentials.

## Gate before tools

Missing evidence → native `pre_tool_call` blocks `kanban_complete` → run the approved test challenge → supply evidence → completion is allowed. Tampering blocks again.

The completion policy requires full **C5 / S11 test-evidence credit**, backed by upstream EXECUTED receipts, and no unresolved P0/P1. The full Production Reality Score is still returned but is **not** a production-readiness claim. A narrowly tested fixture can pass this completion policy while its production score remains low. Neither a claim string nor caller-issued receipt is enough. The claim labels the request; the engine does not independently prove the prose claim or acceptance criteria. Human judgment/review still applies.

This enforces the exact `kanban_complete` tool via the native hook dispatcher, not arbitrary final prose, terminal commands, external board clients, namespaced proxies, or `kanban_request_review`. Other tools proceed normally. It is a completion-tool gate, not a universal trusted execution boundary. Disable it to roll back; no board/database migration.

## Install and configure

Install the reviewed repository pin/subdirectory using the catalog entry in `catalog/checkyourself-evidence-gate.yaml`. Enable via `hermes plugins enable checkyourself-evidence-gate`. The manifest floor is Hermes 0.23.0; integration was actually tested on 0.23.0+48 at e76fbd80be65ea5c1b89831f8d7aaedb713f5cac, on Linux. macOS uses the same POSIX process-group logic but is not verified here. Windows is unsupported.

Set the nonsecret launch environment `CHECKYOURSELF_SCAN_ROOT=/absolute/trusted/project` and, only after inspecting/approving commands, `CHECKYOURSELF_ALLOW_CHALLENGES=1`. These are process-scoped operator settings, not credentials; separate processes/roots for separate profiles. There is no implicit cwd fallback. Set `hermes config set plugins.hook_callback_timeout 25` for the gate's bounded 20-second MCP budget (a slower default fails closed). Slow challenges need shortening; do not silently disable the gate. Timeout terminates the dedicated MCP process group. A challenge deliberately escaping its process group is outside this trusted-project model.

Prepare evidence using the normal upstream challenge CLI (see repository `docs/cli.md`). Pass:

```json
{"metadata":{"checkyourself":{"findings":"findings.json","coverage":"coverage.json","claim":"The focused regression tests pass"}}}
```

The two files must resolve inside the chosen root and each be at most 1 MiB. Coverage uses the ordinary upstream S11 surface and EXECUTED challenge receipts. Source/config/output tampering or missing local integrity binding blocks. The `checkyourself_evidence_score` tool accepts the inner object; `/evidence-gate` and `hermes evidence-gate` accept its JSON serialization. Registration is inert, without network, file reads or secrets.

## Reproducible source-only build

This subtree's tools/schemas/package.json/LICENSE are a byte-for-byte snapshot from KyaniteLabs/checkyourself commit b2a5684bf9e5232f2c945060dbac8a76c0517d6a. `python3 tools/build_hermes_plugin.py` checks them; `--write` regenerates only from that local Git object, never the network. Native registration/demo/catalog layout derives from shared scaffold b0ff57e17ffd2403647e8bdc87c928b0805bb6f3. No new runtime dependency. Pytest is a demo/test dependency, not shipped with the plugin. No compiled payloads.

Run from the repository root:

```sh
python3 tools/build_hermes_plugin.py
python3 -m unittest discover -s tests -v
hermes plugins validate hermes-plugin --json
# Fresh scratch HERMES_HOME; may bootstrap the installed Hermes runtime there:
CHECKYOURSELF_RUNTIME_TEST=1 CHECKYOURSELF_TEST_PYTHON=/usr/bin/python3 HERMES_HOME="$PWD/.demo-home" hermes --run-module unittest discover -s "$PWD/tests" -p test_hermes_runtime.py -v
```

Use a Python with pytest installed for CHECKYOURSELF_TEST_PYTHON. The native demo installs a local copy into the fresh isolated profile, runs real hook dispatch + real registered tool + real MCP, and prints a simulated completion sink (never mutates a real board). Repeat using a fresh disposable home. CI runs unit and validator checks against the exact runtime pin; hosted success must be read from the product PR, not inferred from local output. Security reviews exposure, secret isolation, command trust, blast radius and rollback before merge.
