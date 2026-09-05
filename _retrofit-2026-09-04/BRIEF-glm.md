# ROLE: RISK & SAFETY LENS (GLM-5.3) — checkyourself stage-1
Read _retrofit-2026-09-04/FACTS.md first; it is authoritative.
Your lens: RISK, SECURITY, SAFETY OF THE PRODUCT ITSELF:
- The product audits OTHER apps — does it avoid harming them? scan behavior read-only guarantees (--no-write default posture), secret-handling rules (SKILL.md safety section) vs tools implementation: could a scan leak, write, or execute anything?
- Injection surfaces: the skill instructs agents to read repo files; any place untrusted repo content flows into prompts/eval without labeling?
- Dockerfile/supply chain: base image, pinned deps, what runs at build/run.
- SECURITY.md claims vs reality; NOTICE/LICENSE obligations (attribution blocks) intact.
- Failure modes that would embarrass the product publicly (wrong P0 verdicts, score inflation paths the code allows).
Output ONLY: _retrofit-2026-09-04/FINDINGS-glm.md (FACTS output contract).
