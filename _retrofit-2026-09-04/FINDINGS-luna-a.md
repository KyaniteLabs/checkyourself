# Correctness Findings — luna-a

Verdict: RETROFIT-NEEDED yes — confirmed scanner blind spots, score and validation bypasses, symlink-boundary failures, malformed-input crashes, and incorrect diff/history receipts.

## Findings

### LUNA-001 — P1 — Scanner content limits make clean results look complete

- Evidence: `tools/checkyourself.py:294-302`, `tools/checkyourself.py:477-480`, `tools/checkyourself.py:614`

  ```python
  return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
  ```
- `tools/checkyourself.py:477-480` separately contains:

  ```python
  if real.stat().st_size > 2_000_000:
      continue
  ```

  `tools/checkyourself.py:614` separately contains:

  ```python
  text = read_text(p, max_chars=60_000)
  ```
- Failure: input `app.py` with a credential after character 60,000 produced no `CY-SECRET-001`; input `large.py` over 2,000,000 bytes was omitted with `files_scanned: 0`, `truncated: false`, and no skip count. Read failures also return empty text without incrementing `files_unreadable`.
- Fix sketch: scan full eligible content or record byte truncation/oversize/read failures in the result and make incomplete scans remain explicitly unknown.

### LUNA-002 — P1 — Extensionless configuration files bypass content detectors

- Evidence: `tools/checkyourself.py:612-614`

  ```python
  if suffix not in TEXT_EXTENSIONS and not name.startswith(".env") and kind is None:
      continue
  text = read_text(p, max_chars=60_000)
  ```
- Failure: input `Dockerfile` containing a credential-shaped `ENV API_KEY=...` produced only test/CI findings. `Dockerfile` is a stack signal, but its empty suffix prevents secret, default-credential, debug, CORS, and sink checks. `Makefile` and `Jenkinsfile` have the same gap.
- Fix sketch: classify known extensionless basenames and run the applicable detectors on them.

### LUNA-003 — P2 — A valid non-object `package.json` crashes scanning

- Evidence: `tools/checkyourself.py:505-509`

  ```python
  if package_json.exists():
      try:
          data = json.loads(read_text(package_json))
          if isinstance(data.get("scripts"), dict):
  ```
- Failure: input `package.json` containing valid JSON `[]` exited with an uncaught `AttributeError: 'list' object has no attribute 'get'` and traceback instead of a stable shape error or finding.
- Fix sketch: require a dictionary after parsing and return a stable input/configuration result for other JSON types.

### LUNA-004 — P1 — Test discovery treats ordinary filenames as automated tests

- Evidence: `tools/checkyourself.py:669-676`

  ```python
  lower = rp.lower()
  if any(x in lower for x in ("test", "spec", "__tests__", "playwright", "cypress")):
      if p.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".java", ".rb", ".rs"}:
  ```
- Failure: input project containing only `latest.py` was returned in `tests` and omitted `CY-TEST-001`; `latest` contains the substring `test` but is not a test file. This can remove a P1 finding and make scan-derived scoring more favorable without any test.
- Fix sketch: match test directories and filename conventions such as `test_*.py`, `*_test.go`, `*.spec.ts`, and explicit test roots.

### LUNA-005 — P2 — Invalid suppression configuration is hidden or crashes the scan

- Evidence: `tools/checkyourself.py:394-405`, `tools/checkyourself.py:1001-1002`

  ```python
  except json.JSONDecodeError:
      return {"suppress": [], "config_error": f"{name} could not be parsed as JSON"}
  ```

  ```python
  config = load_checkyourself_config(root)
  finding_dicts = apply_suppressions([f.to_dict() for f in findings], config.get("suppress") or [])
  ```
- Failure: input malformed `.checkyourself.json` returned exit 0 with no `config_error` in the scan output, so requested configuration was silently ignored. Input `{"suppress": "not-a-list"}` reached `suppression_matches` as a string and crashed with `AttributeError`.
- Fix sketch: validate config shape, surface parse/shape errors in the scan contract, and never coerce invalid suppression data into an empty list.

### LUNA-006 — P2 — `.gitignore` checks use substring search instead of pattern semantics

- Evidence: `tools/checkyourself.py:533-535`, `tools/checkyourself.py:749-750`, `tools/checkyourself.py:845-846`

  ```python
  def gitignore_entries(root: Path) -> str:
      gi = root / ".gitignore"
      return read_text(gi).lower() if gi.exists() else ""
  ```

  ```python
  env_ignored = ".env" in gitignore
  ```
- Failure: input `.env` with `.gitignore` containing only `!.env` omitted the P0-style `CY-ENV-001`, even though the negation re-includes the secret file; a comment containing `.env` has the same false-protection effect. Pattern semantics are not evaluated, so comments and negations cannot be distinguished from an actual ignore rule.
- Fix sketch: parse comments, negations, anchoring, and directory-aware glob rules, then evaluate the exact path.

### LUNA-007 — P2 — Supported env-example variants still trigger “no example”

- Evidence: `tools/checkyourself.py:538-543`, `tools/checkyourself.py:864-865`

  ```python
  def is_env_example_name(name: str) -> bool:
      lower = name.lower()
      return lower in ENV_EXAMPLE_NAMES or (
          lower.startswith(".env")
          and lower.endswith((".example", ".sample", ".template"))
      )
  ```
- `tools/checkyourself.py:864-865` separately contains:

  ```python
  has_example = any(Path(e).name.lower() in ENV_EXAMPLE_NAMES for e in env_files)
  ```
- Failure: input `.env` plus `.env.local.example` was classified in `env_files` but still emitted `CY-ENV-003`; the broad classifier and exact-name check disagree.
- Fix sketch: compute `has_example` with `is_env_example_name(Path(e).name)`.

### LUNA-008 — P1 — Coverage statuses can forge a high-confidence perfect score

- Evidence: `tools/checkyourself.py:1316-1340`, `tools/checkyourself.py:1452-1463`, `tools/checkyourself.py:1503-1527`

  ```python
  status_rank = {"Finding": 4, "Unknown": 3, "Pass": 2, "NotApplicable": 1}
  ```
- `tools/checkyourself.py:1331-1332` separately contains:

  ```python
  status = item.get("status") or "Unknown"
  evidence = [str(x) for x in item.get("evidence_reviewed") or []]
  ```

  `tools/checkyourself.py:1452-1463` separately contains:

  ```python
  status = coverage_state["status"]
  if status == "Unknown":
      missing = coverage_state["missing_evidence"] or ["evidence missing for this category"]
      if cid in CRITICAL_CATEGORIES:
          awarded = 0.0
          penalties.append({"reason": "critical coverage unknown", "points": weight, "missing_evidence": missing})
      else:
          reduction = weight * 0.50
          awarded -= reduction
          penalties.append({"reason": "coverage unknown", "points": round(reduction, 2), "missing_evidence": missing})
  elif status == "MissingCoverage":
      penalties.append({"reason": "coverage artifact not supplied", "points": 0, "missing_evidence": coverage_state["missing_evidence"]})
  ```
- Failure: input coverage with all 20 surfaces set to `Finding` and no evidence returned `score: 100`, `confidence: "high"`, `coverage_complete: true`, and no manual evidence. The same result occurred for invalid status `Bogus`. `score` does not call `coverage_check`, and `Finding`/unrecognized statuses receive no scoring penalty.
- Fix sketch: validate canonical IDs, categories, statuses, and required evidence before scoring; downgrade malformed or unsupported entries to `Unknown` and apply caps.

### LUNA-009 — P1 — Bundled schema validation ignores `oneOf`

- Evidence: `tools/checkyourself.py:1813-1833`, `schemas/dashboard-data.schema.json:5`

  ```python
  if "type" in schema and not type_matches(data, schema["type"]):
      errors.append(f"{path}: expected {schema['type']}, got {json_type_name(data)}")
      return errors
  ```

  ```python
  props = schema.get("properties", {})
  ```

  ```json
  "oneOf": [
  ```
- Failure: input `validate --kind dashboard-data` with JSON `[]` returned `valid: true`, although neither required object branch can match. The `dashboard` alias uses the same bypass.
- Fix sketch: implement `oneOf` branch validation or fail closed when a bundled schema contains an unsupported keyword.

### LUNA-010 — P2 — `diff` misses status-only resolutions

- Evidence: `tools/checkyourself.py:1592-1596`

  ```python
  added_ids = sorted(set(new_findings) - set(old_findings))
  resolved_ids = sorted(set(old_findings) - set(new_findings))
  persisting_ids = sorted(set(old_findings) & set(new_findings))
  ```
- Failure: input old finding `F-1` with `status: open` and new `F-1` with `status: fixed` returned `resolved: []`, `unchanged: ["F-1"]`, even though counts dropped from P1=1 to P1=0. The receipt hides the resolution event.
- Fix sketch: emit status changes and classify open-to-resolved transitions explicitly.

### LUNA-011 — P2 — Output safety checks only the leaf symlink

- Evidence: `tools/checkyourself.py:1881-1889`

  ```python
  if path.is_symlink():
      raise CliError(f"refusing to write through symlink: {path}")
  path.write_text(body, encoding="utf-8")
  ```
- Failure: input `--out project/linked/context.md` where `project/linked` is a symlink to another directory exited 0 and wrote `context.md` in the symlink target. The leaf is ordinary, so the guard does not detect the parent redirect.
- Fix sketch: resolve and constrain every parent component to the intended boundary, or use directory descriptors with no-follow protections.

### LUNA-012 — P2 — Coverage input shape errors crash the CLI

- Evidence: `tools/checkyourself.py:1160-1165`

  ```python
  def coverage_check(data: dict) -> dict:
      errors: List[str] = []
      warnings: List[str] = []
      surfaces = data.get("surfaces") or data.get("coverage") or []
      if not isinstance(surfaces, list):
  ```
- Failure: input `coverage --check` with valid JSON `[]` exited 1 with an uncaught `AttributeError` traceback instead of the documented validation result. A list supplied to `score --coverage` follows the same `.get` assumption.
- Fix sketch: type-check top-level artifacts before property access and return a structured invalid result or `CliError(code=2)`.

### LUNA-013 — P2 — MCP input types are declared but truthily coerced

- Evidence: `tools/checkyourself.py:2175-2186`, `tools/checkyourself.py:2359-2361`

  ```python
  "deep": {
      "type": "boolean",
      "description": "Run slower validation checks for detected surfaces, such as mutable GitHub Action references. Defaults to false.",
  },
  "max_files": {
      "type": "integer",
      "description": "Maximum files to scan before truncating (default 6000). The result reports truncation in scan_limits.",
  },
  ```

  ```python
  max_files = int(arguments.get("max_files") or DEFAULT_MAX_FILES)
  return scan(project, deep=bool(arguments.get("deep")), max_files=max_files)
  ```
- Failure: input MCP `{"deep":"false"}` returned `deep: true`; input `{"max_files":0}` scanned the default 6000-file cap instead of zero files. Invalid strings can also raise conversion errors rather than a protocol `-32602`.
- Fix sketch: validate primitive types and bounds before conversion; honor zero and reject invalid values.

### LUNA-014 — P2 — Public required-file validation accepts directories and symlinks

- Evidence: `tools/validate_public.py:187-190`

  ```python
  def validate_required(root: Path, errors: list[str]) -> None:
      for rel in REQUIRED:
          if not (root / rel).exists():
              errors.append(f"missing required public file: {rel}")
  ```
- Failure: input root with a directory named `README.md` produced no missing-README error; an existing symlink can likewise satisfy this check even though `public_files()` excludes symlinked files from validation.
- Fix sketch: require `is_file()`, reject symlinks, and enforce resolved containment for required paths.

### LUNA-015 — P2 — Public asset validation follows symlinks outside the root

- Evidence: `tools/validate_public.py:316-321`

  ```python
  for path in sorted(assets.iterdir()):
      if not path.is_file():
          continue
      digest = hashlib.sha256(path.read_bytes()).hexdigest()
  ```
- Failure: input `assets/two.bin` symlinked to an external file was read and reported as a duplicate of `assets/one.bin`, while the main `public_files()` walk correctly skips symlinks. The validator therefore crosses its own public-root boundary.
- Fix sketch: skip symlinks, enforce resolved containment, and handle read/stat failures consistently with `public_files()`.

### LUNA-016 — P3 — Markdown links with titles are falsely reported broken

- Evidence: `tools/validate_public.py:288-300`

  ```python
  link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
  ```

  ```python
  raw = match.group(1)
  link = raw.split("#")[0].strip()
  target = (path.parent / urllib.parse.unquote(link)).resolve()
  ```
- Failure: a titled link to `target.md` with an existing target was reported as
  broken because the parser treated the title as part of the destination.
- Fix sketch: parse the Markdown destination separately from an optional title, including angle-bracket destinations.

### LUNA-017 — P2 — Negative `--max-files` produces an invalid successful scan

- Evidence: `tools/checkyourself.py:2505-2506`, `tools/checkyourself.py:487-492`

  ```python
  parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES,
                      help=f"Maximum files to scan before truncating (default {DEFAULT_MAX_FILES}). Truncation is disclosed in scan_limits.")
  ```

  ```python
  if len(files) >= limit:
      stats["truncated"] = True
      stats["files_beyond_limit"] += 1
  ```
- Failure: input `scan --max-files -1` exited 0 with `files_scanned: 0`, `scan_limits.max_files: -1`, and a scan artifact that fails its own schema minimum of zero.
- Fix sketch: reject negative limits at argument/MCP boundaries with a stable usage error.

### LUNA-018 — P2 — Skipped symlinked directories are omitted from scan accounting

- Evidence: `tools/checkyourself.py:448-454`, `tools/checkyourself.py:467-470`

  ```python
  # Never descend symlinked directories: they can escape the project tree.
  return not (parent / name).is_symlink()
  ```

  ```python
  dirnames[:] = sorted(d for d in dirnames if keep_dir(parent, d))
  ```
- Failure: input project with a symlinked directory containing files returned `symlinks_skipped: 0` and `truncated: false`; the directory was not scanned but the result did not disclose the skipped path.
- Fix sketch: count filtered symlink directories in `scan_limits` and keep the disclosure wording aligned with the actual walk.

### LUNA-019 — P2 — Malformed manifest shapes crash public validation

- Evidence: `tools/validate_public.py:248-270`

  ```python
  for name, rel in manifest.get("entrypoints", {}).items():
      if not (root / rel).exists():
          errors.append(f"manifest entrypoint is missing: {name} -> {rel}")
  ```
- Failure: input valid JSON manifest `{"entrypoints": []}` caused an uncaught `AttributeError: 'list' object has no attribute 'items'` and traceback. Other valid-but-wrong shapes for `modes` or `optional_dashboard` similarly reach unchecked operations.
- Fix sketch: validate manifest object fields and report shape errors without traceback.

### LUNA-020 — P1 — CI discovery follows workflow symlinks and can mark absent CI as present

- Evidence: `tools/validate_public.py:169-181` establishes the project’s symlink exclusion; `tools/checkyourself.py:680-688` does not apply it.

  ```python
  def find_ci(root: Path) -> List[str]:
      ci: List[str] = []
      wf = root / ".github" / "workflows"
      if wf.exists():
          ci.extend(sorted(rel(root, p) for p in wf.glob("*") if p.is_file()))
  ```
- Failure: input `.github/workflows/ci.yml` symlinked to an external file was listed in `ci`, while `read_text()` refused to read it. The scan therefore omitted `CY-CI-001` and inferred C6 CI coverage from a workflow it did not inspect.
- Fix sketch: require regular non-symlink workflow files and use the same bounded walk for CI discovery and content reads.

### LUNA-021 — P1 — Symlinked CheckYourself config can suppress findings out of tree

- Evidence: `tools/checkyourself.py:394-405`

  ```python
  path = root / name
  if not path.exists():
      continue
  ```

  ```python
  return {"suppress": parse_minimal_yaml_suppressions(path.read_text(encoding="utf-8"))}
  ```
- Failure: input `.checkyourself.yml` symlinked to an external suppression file was followed by `load_checkyourself_config`, even though `iter_files()` skipped symlinks. External suppressions can hide findings and are absent from `scan_limits`.
- Fix sketch: reject symlinked config paths and require the resolved config file to remain under the scan root.

### LUNA-022 — P2 — Semantically corrupt score history is overwritten without backup

- Evidence: `tools/checkyourself.py:1944-1961`

  ```python
  if path.exists():
      try:
          parsed = json.loads(path.read_text(encoding="utf-8"))
          if isinstance(parsed, list):
              history = [item for item in parsed if isinstance(item, dict)]
  ```
- `tools/checkyourself.py:1960-1961` separately contains:

  ```python
  history.append(entry)
  safe_write_text(path, json.dumps(history, indent=2) + "\n")
  ```
- Failure: input existing history `{}` was treated as an empty list and overwritten by the next score receipt; only JSON syntax errors receive a `.corrupt.bak`. The prior valid JSON audit record is lost.
- Fix sketch: validate the history shape and preserve any non-list or malformed entry before starting a fresh ledger.

### LUNA-023 — P3 — Deep CI checks flag comments and shell strings as workflow controls

- Evidence: `tools/checkyourself.py:695-712`

  ```python
  action_re = re.compile(r"uses:\s*['\"]?([^@\s'\"]+)@([^@\s'\"]+)", re.I)
  npm_install_re = re.compile(r"\bnpm\s+install\b(?!\s+-g)")
  ```

  `tools/checkyourself.py:703-712` separately contains:

  ```python
  match = action_re.search(line)
  if npm_install_re.search(line):
  ```
- Failure: input workflow comment `# uses: vendor/action@v1` or `# npm install` emitted mutable-action or npm-install findings even though no workflow step executes it.
- Fix sketch: parse YAML step structure or at minimum ignore comments and non-command scalar text before applying these checks.

## Verification

- `scan samples --deep --no-write --format json`: exit 0; 4 files; counts P0=0, P1=1, P2=1, P3=1; no truncation. `coverage --emit --format json`: exit 0 with 20 surfaces. A filled 20-row coverage artifact passed `coverage --check` with `complete: true`, `surface_count: 20`, and `errors: []` (warnings only for non-file evidence); score, backlog, next, diff, and artifact validation all returned exit 0. The sample score remained capped by its unresolved P1 test finding.
- Adversarial probes reproduced: `package.json: []` traceback; malformed suppression shape traceback; `.env` plus `!.env` false protection; `.env.local.example` false `CY-ENV-003`; tail credential omission; >2 MB omission without disclosure; `latest.py` false test; `--max-files -1` successful invalid output; `coverage --check []` traceback; dashboard-data `[]` accepted as valid; all-`Finding`/`Bogus` coverage scored 100/high; fixed-status diff reported unchanged; parent symlink output wrote target; MCP `deep: "false"` became true and `max_files: 0` became 6000; malformed manifest traceback; asset symlink was read; Markdown title was falsely broken; symlinked directories/config/workflows bypassed disclosure or safety.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/ -q`: 59 passed, 1 failed. The failure is `test_real_repository_passes_validation`, caused by `README.md:200` linking to missing `10_DASHBOARD/output/checkyourself-dogfood-dashboard-screenshot.png`; this is outside the requested code paths.
- AST parsing passed for both tools and both test modules. No defect was confirmed in Dockerfile or the five adapter documents by static inspection.

## Coverage

- Swept all functions in `tools/checkyourself.py` and `tools/validate_public.py`.
- Swept all JSON contracts in `schemas/`, both test modules, `Dockerfile`, and all five files in `06_ADAPTERS/`.
- Used the repository code graph before targeted source reads, then exercised deterministic CLI, MCP, schema, symlink, path, malformed-input, and history cases in temporary scratch directories under `_retrofit-2026-09-04/`.
- No files outside `_retrofit-2026-09-04/` were modified.

## Unknowns

- No network, image build, or external MCP host was used; Docker runtime availability and host-side JSON-schema enforcement remain unverified.
- The existing public-validation failure may reflect a missing tracked artifact outside this role’s allowed code paths; it was not changed.
- No remediation was applied; default-branch, CI, and deployment state remain unverified.

## IMPROVEMENTS

- Improve scan completeness accounting. WHY: byte limits, oversized files, unreadable files, and symlink directories can look like clean coverage. FIX: emit explicit skip/truncation counters and make incomplete scans remain unknown.
- Centralize fail-closed artifact validation. WHY: score bypasses `coverage_check`, and the custom schema walker accepts unsupported `oneOf` payloads. FIX: validate canonical coverage and schema keywords before scoring or reporting success.
- Add adversarial regression tests. WHY: malformed shapes, parent symlinks, pattern comments, status transitions, and MCP coercions passed the current happy-path suite. FIX: add one focused test per confirmed repro and keep the full suite green.
