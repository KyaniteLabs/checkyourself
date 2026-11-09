# Evidence-gate demo — target under 90 seconds

This is a narration script for `demo/gate_demo.py`. The script is the proof. It does not start Hermes, publish npm, or touch a gateway.

0–15s: “A completion claim is not a score.” Show `kanban_complete` with no evidence. The native `pre_tool_call` hook blocks it.

15–40s: Show the tiny local fixture and the read-only scan. The gate prints that scan’s score and blocks or allows exactly when the score has no open P0 or P1. Say that a passing gate is not a production-safety certification.

40–60s: Score a findings file with no open P0/P1. The same hook now allows `kanban_complete`. Read the score out loud.

60–75s: Add one open P0. The hook blocks again and the message includes that score.

75–90s: Point at `plugin.yaml` (`pre_llm_call`, `pre_tool_call`, `post_tool_call`) and `catalog/PR-BODY.md`. npm publish stays with Maintainer. No catalog PR has been opened from this repo.

## Run

```bash
python3 plugins/checkyourself-hermes/demo/gate_demo.py
```

The command prints `elapsed_seconds=` and exits 0 only when the four gate checks pass in under 90 seconds. It writes under a temporary `HERMES_HOME` and leaves the real one alone.
