# Adapter Guidance

The core pack is intentionally model-agnostic. Adapters should map these capability folders into the conventions of a specific runtime without changing the core behavior.

## Adapter patterns

| Runtime style | Adapter approach |
|---|---|
| Folder-based skill loading | Install each folder under `capabilities/` as a separate capability. |
| Repository-level instructions | Add `AGENTS.md` to the repository root and keep `MANIFEST.yaml` in context. |
| IDE assistant | Pin `AGENTS.md`, `MANIFEST.yaml`, and selected capability files in the assistant context. |
| CI/CD enforcement | Convert gates into deterministic jobs: tests, scans, policy-as-code, deploy checks. |
| Multi-agent orchestrator | Use `MANIFEST.yaml` as the routing registry and capability ids as worker names. |

## Adapter rule

Keep platform-specific setup outside the core capability files. The core should remain portable across model providers, IDEs, local agents, and enterprise orchestrators.
