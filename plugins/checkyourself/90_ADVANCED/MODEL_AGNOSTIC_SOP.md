# SOP: Research Document to Model-Agnostic Capability Pack

## Principle

Do not mirror the document table of contents. Extract repeatable work an agent should perform.

## Process

1. **Identify the agent task.** Write each candidate as `verb + object + condition`.
2. **Merge by workflow.** If two tasks are always performed together, make one capability.
3. **Split by risk boundary.** If one topic contains separate safety responsibilities, split it even if the document has one chapter.
4. **Write activation metadata.** The description and trigger list must explain when to use the capability.
5. **Keep the core file lean.** Put detailed examples, references, and templates in separate files.
6. **Define outputs.** A capability without an output shape produces inconsistent work.
7. **Define verification.** Every recommendation should point to tests, scans, telemetry, review, or explicit assumptions.
8. **Package for portability.** Avoid vendor-specific tool names in core files. Put platform adapters outside the core.
9. **Test with realistic prompts.** Verify triggering, output quality, and correct hand-offs.
10. **Ship with validation.** Include a manifest, templates, references, and a script that checks structure.

## Decision rules

| Signal | Result |
|---|---|
| Repeatable work with clear trigger | Capability |
| Long rationale or deep examples | Reference |
| Deterministic repetitive check | Script or CI gate |
| Mandatory org rule | Policy-as-code or CI gate |
| One-off context | Keep as project documentation |

## Quality bar

A publishable capability has: name, description, triggers, inputs, outputs, protocol, gates, anti-patterns, examples, hand-offs, and references.
