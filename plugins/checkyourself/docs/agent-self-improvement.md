# Agent Self-Improvement Notes

CheckYourself improves when real audits expose gaps in how the agent works.
These notes are durable operating lessons, not a trophy shelf.

## 2026-05-29: Dependabot `glib` remediation

Source: resolving the final medium Dependabot alert in
`simongonzalezdc/content-production-system`.

### What happened

The app had a Rust Dependabot alert for `glib`. A normal version bump was not
available because Tauri's Linux GTK dependency chain still resolved through
`gtk 0.18`, which requires the vulnerable `glib 0.18` line. The final fix
vendored `glib 0.18.5`, backported the upstream `VariantStrIter` pointer fix,
patched Cargo to use the local crate, and verified that GitHub marked the
default-branch alert as fixed after merge.

### Agent lessons

- Local success is not closure. A security finding is done only when the live
  alert state, default-branch CI, scanner output, and git branch state agree.
- Lockfile source matters. The same version string can mean different risk when
  it comes from crates.io, a fork, a vendored source, or a local patch.
- CI infrastructure is part of production readiness. A blocked hosted runner or
  missing self-hosted toolchain can make a repo look remediated locally while
  GitHub remains unable to prove it.
- Dependency remediation needs root-cause discipline. If upstream constraints
  prevent the obvious package bump, document the path, patch narrowly, and
  leave a removal path for the future upstream fix.
- Broad searches need guardrails. Exclude generated output, dependency folders,
  build artifacts, and vendored code unless those paths are the actual subject.

### Completion standard

For future dependency/security remediation, the agent should report:

- the dependency or vulnerable control path;
- the fix strategy used;
- focused local proof;
- normal repo checks;
- PR and merge status;
- default-branch CI status;
- live dependency/security alert state;
- clean and synced git state;
- remaining proof gaps, if any.

The practical rule: if the user asks whether everything is at 100%, do not
answer from one surface. Make the receipts agree first.
