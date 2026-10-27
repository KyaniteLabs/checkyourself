"""Argument parser, command handlers, and the main entry point."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys
from typing import List, Optional, Sequence
from .challenge_run import challenge_from_root
from .constants import COVERAGE_SURFACES, DEFAULT_COVERAGE_PATH
from .coverage import coverage_check, coverage_emit
from .describe import describe_capabilities, load_schema, schema_registry
from .errors import CLI_ENTRY, CliError, cli_reinvocation, cli_retry_for
from .jsonlite import load_json_arg
from .mcp import run_mcp_server
from .output import append_score_history, resolve_history_path, safe_write_text, write_json, write_text_result
from .planning import backlog_from_findings, diff_findings, next_from_findings
from .project import init_project
from .receipts import issue_receipt
from .report import render_markdown
from .scan import scan
from .scanning import DEFAULT_MAX_FILES
from .scoring import score_from_inputs
from .validation import validate_artifact


def command_scan(args: argparse.Namespace) -> int:
    root = Path(args.project).resolve()
    if not root.is_dir():
        raise CliError(f"project root not found: {root}")
    data = scan(root, deep=getattr(args, "deep", False), max_files=getattr(args, "max_files", DEFAULT_MAX_FILES))
    json_stdout = args.format == "json" or args.json == "-" or (args.no_write and args.json is not None)

    if not args.no_write and args.out is not None:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        safe_write_text(out, render_markdown(root, data))
        if not args.quiet and not json_stdout:
            print(f"Wrote context: {out}")

    if not args.no_write and args.json is not None and args.json != "-":
        jout = Path(args.json)
        if not jout.is_absolute():
            jout = Path.cwd() / jout
        safe_write_text(jout, json.dumps(data, indent=2, allow_nan=False) + "\n")
        if not args.quiet and not json_stdout:
            print(f"Wrote JSON:    {jout}")

    if json_stdout:
        write_json(data)
    elif not args.quiet:
        write_text_result(data)

    if args.ci and data["counts"].get("P0", 0) > 0:
        return 1
    return 0


def command_describe(args: argparse.Namespace) -> int:
    data = describe_capabilities()
    if args.format == "json":
        write_json(data)
    else:
        print(f"CheckYourself {data['version']} commands:")
        for command in data["commands"]:
            print(f"- {command['name']}: {command['summary']}")
    return 0


def command_schema(args: argparse.Namespace) -> int:
    write_json(load_schema(args.name))
    return 0


def command_coverage(args: argparse.Namespace) -> int:
    if args.check:
        data = load_json_arg(args.check)
        evidence_root = Path.cwd() if args.check == "-" else Path(args.check).resolve().parent
        result = coverage_check(data, evidence_root)
        if args.format == "json":
            write_json(result)
        else:
            print("Coverage complete" if result["complete"] else "Coverage incomplete")
            for error in result["errors"]:
                print(f"- {error}")
            for warning in result["warnings"]:
                print(f"- warning: {warning}")
        return 0 if result["complete"] else 1
    data = coverage_emit(args.project or "")
    out_path = args.out
    if not out_path and args.format == "text":
        out_path = DEFAULT_COVERAGE_PATH
    if out_path:
        safe_write_text(Path(out_path), json.dumps(data, indent=2, allow_nan=False) + "\n")
    if args.format == "json":
        write_json(data)
    else:
        print(f"Wrote coverage skeleton: {out_path}")
        print("Fill coverage.json with evidence, then re-run score.")
    return 0


def command_challenge(args: argparse.Namespace) -> int:
    root = Path(args.root or args.project).resolve()
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = root / output_dir
    result = challenge_from_root(root, args.surface, output_dir)
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        safe_write_text(out, json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if args.format == "json":
        write_json(result)
    else:
        print("Challenges passed" if result["complete"] else "Challenges incomplete")
        for item in result["surfaces"]:
            print(f"- {item['surface_id']}: {item['status']}")
            for reason in item.get("reasons") or []:
                print(f"  {reason}")
        print(f"Receipts: {len(result['receipts'])}")
    return 0 if result["complete"] else 1


def command_receipt(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise CliError(f"receipt evidence root not found: {root}")
    receipt = issue_receipt(
        args.reference,
        root,
        surface_id=args.surface_id,
        source_revision=args.source_revision,
        command=args.command,
        claim=args.claim,
        result=args.result,
        source_state=args.source_state,
        subject_digest=args.subject_digest,
    )
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        safe_write_text(out, json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    if args.format == "json":
        write_json(receipt)
    else:
        if args.out:
            print(f"Wrote verifier receipt: {args.out}")
        else:
            print(json.dumps(receipt, indent=2, allow_nan=False))
    return 0


def command_score(args: argparse.Namespace) -> int:
    findings_data = load_json_arg(args.findings)
    if args.coverage is not None:
        coverage_root = Path.cwd() if args.coverage == "-" else Path(args.coverage).resolve().parent
        result = score_from_inputs(
            findings_data,
            load_json_arg(args.coverage),
            evidence_root=coverage_root,
            claim=args.claim,
        )
    else:
        result = score_from_inputs(findings_data, claim=args.claim)
    history_path = resolve_history_path(args.findings, args.history)
    append_score_history(history_path, result, args.note)
    if args.format == "json":
        write_json(result)
    else:
        write_text_result(result)
        if history_path is not None:
            print(f"History: {history_path}")
    return 0


def command_backlog(args: argparse.Namespace) -> int:
    data = load_json_arg(args.findings)
    result = backlog_from_findings(data)
    if args.format == "json":
        write_json(result)
    else:
        write_text_result(result)
    return 0


def command_next(args: argparse.Namespace) -> int:
    data = load_json_arg(args.findings)
    result = next_from_findings(data)
    if args.format == "json":
        write_json(result)
    else:
        write_text_result(result)
    return 0


def command_diff(args: argparse.Namespace) -> int:
    result = diff_findings(load_json_arg(args.old), load_json_arg(args.new))
    if args.format == "json":
        write_json(result)
    else:
        added = result["added"]
        resolved = result["resolved"]
        print(f"Added: {len(added)}, Resolved: {len(resolved)}, Unchanged: {len(result['unchanged'])}")
        for f in added:
            print(f"  + [{f['severity']}] {f['id']} {f['finding']}")
        for f in resolved:
            print(f"  - [{f['severity']}] {f['id']} {f['finding']}")
        for event in result["regressions"]:
            print(f"  ! [{event['type']}] {event['id']}")
        if result["count_regression"]:
            print("  ! [count_increased] open P0/P1 count increased against the baseline.")
    if args.ci and result["regression"]:
        return 1
    return 0


def command_validate(args: argparse.Namespace) -> int:
    data = load_json_arg(args.file)
    result = validate_artifact(args.kind, data)
    if args.format == "json":
        write_json(result)
    else:
        print("Valid" if result["valid"] else "Invalid")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["valid"] else 1


def command_init(args: argparse.Namespace) -> int:
    result = init_project(Path(args.project), force=args.force)
    if args.format == "json":
        write_json(result)
    else:
        for path in result["created"]:
            print(f"Created: {path}")
        for path in result["skipped"]:
            print(f"Skipped existing: {path}")
    return 0


class CheckYourselfParser(argparse.ArgumentParser):
    """ArgumentParser whose usage errors name one concrete retry re-invocation."""

    def error(self, message: str) -> None:
        verb = self.prog.split()[-1]
        retry = cli_reinvocation(verb) if " " in self.prog else f"{CLI_ENTRY} --help"
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\nretry: {retry}\n")


def add_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project", nargs="?", default=".", help="Project root to scan (default: .)")
    parser.add_argument("--out", help="Write Markdown context to this path (scans are stdout-only by default)")
    parser.add_argument(
        "--json",
        nargs="?",
        const="CHECKYOURSELF_SCAN.generated.json",
        default=None,
        help="Also write a JSON summary (default path: CHECKYOURSELF_SCAN.generated.json). Use - for stdout.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Console output format. Use json for machine-readable stdout.",
    )
    parser.add_argument("--ci", action="store_true", help="Exit non-zero if any P0 finding is detected.")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Run slower validation checks for detected surfaces, such as mutable CI actions and dependency-update cove"
        "rage.",
    )
    parser.add_argument("--no-write", action="store_true", help="Print the summary only; write no files.")
    parser.add_argument("--quiet", action="store_true", help="Suppress the console summary.")
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"Maximum files to scan before truncating (default {DEFAULT_MAX_FILES}). "
        "Truncation is disclosed in scan_limits.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = CheckYourselfParser(
        prog="checkyourself",
        description="Local deterministic interface for CheckYourself diagnostics.",
    )
    sub = parser.add_subparsers(dest="command", required=True, parser_class=CheckYourselfParser)

    p = sub.add_parser("describe", help="Emit the machine-readable capability manifest.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_describe)

    p = sub.add_parser("scan", help="Scan a project and emit deterministic local findings.")
    add_scan_args(p)
    p.set_defaults(func=command_scan)

    p = sub.add_parser(
        "diagnostic", help="Alias for scan; emits deterministic evidence for the manual diagnostic workflow."
    )
    add_scan_args(p)
    p.set_defaults(func=command_scan)

    p = sub.add_parser("schema", help="Print a bundled schema by name.")
    p.add_argument("name", choices=sorted(schema_registry().keys()))
    p.set_defaults(func=command_schema)

    p = sub.add_parser("coverage", help="Emit or check the 20-surface coverage matrix.")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--emit", action="store_true", help="Emit the coverage skeleton (default).")
    group.add_argument("--check", help="Validate a filled coverage JSON file.")
    p.add_argument("--project", default="", help="Optional project label for emitted coverage.")
    p.add_argument("--out", help="Write emitted coverage JSON to this path.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_coverage)

    p = sub.add_parser("challenge", help="Execute committed per-surface challenges and mint verifier-owned receipts.")
    p.add_argument("project", nargs="?", default=".", help="Project root to challenge (default: current directory).")
    p.add_argument("--root", help="Alias for the project root; useful when composing commands.")
    p.add_argument(
        "--surface",
        choices=[sid for sid, _surface, _category in COVERAGE_SURFACES],
        help="Run one canonical surface instead of all configured surfaces.",
    )
    p.add_argument("--output-dir", help="Directory under the project root for captured output and receipts.")
    p.add_argument("--out", help="Write the challenge result JSON to this path.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_challenge)

    p = sub.add_parser("receipt", help="Issue one verifier-hashed receipt for a registered surface artifact.")
    p.add_argument("--reference", required=True, help="In-root registered verification artifact path to hash.")
    p.add_argument(
        "--surface-id",
        required=True,
        choices=[sid for sid, _surface, _category in COVERAGE_SURFACES],
        help="Canonical coverage surface this receipt proves.",
    )
    p.add_argument("--source-revision", required=True, help="Source revision examined when the receipt was issued.")
    p.add_argument(
        "--source-state", required=True, help="Source/environment state examined when the receipt was issued."
    )
    p.add_argument("--command", required=True, help="Command recorded at issuance.")
    p.add_argument("--claim", required=True, help="One claim proved by this receipt.")
    p.add_argument("--result", required=True, help="Observed result recorded at issuance.")
    p.add_argument("--subject-digest", help="Optional content hash assertion for the registered verification artifact.")
    p.add_argument(
        "--root", default=".", help="Evidence root containing the referenced artifact (default: current directory)."
    )
    p.add_argument("--out", help="Write the receipt JSON to this path.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_receipt)

    p = sub.add_parser("score", help="Compute deterministic Production Reality Score.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--coverage", help="Optional coverage JSON file.")
    p.add_argument(
        "--history",
        nargs="?",
        const="",
        help="Write score history to this path (or beside findings when supplied without a path; disabled by default).",
    )
    p.add_argument(
        "--no-history", dest="history", action="store_const", const="none", help="Do not append score history."
    )
    p.add_argument("--note", default="", help="Optional note stored with the score history entry.")
    p.add_argument(
        "--claim",
        help="Optional accepted completion claim to record; evidence remains unbound unless coverage marks it explicitl"
        "y.",
    )
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_score)

    p = sub.add_parser("backlog", help="Rank the complete remediation backlog.")
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_backlog)

    p = sub.add_parser(
        "next", help="Return the next highest-severity unresolved approval batch; safety analysis is not performed."
    )
    p.add_argument("--findings", required=True, help="JSON file containing findings, scan output, or report.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_next)

    p = sub.add_parser("diff", help="Compare two findings artifacts and report added/resolved/regressed findings.")
    p.add_argument("--old", required=True, help="Baseline findings JSON path, or - for stdin.")
    p.add_argument("--new", required=True, help="Current findings JSON path, or - for stdin.")
    p.add_argument(
        "--ci",
        action="store_true",
        help="Exit non-zero for a new/reopened/escalated open P0/P1 finding or an increased open P0/P1 count.",
    )
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_diff)

    p = sub.add_parser("validate", help="Validate a JSON artifact against a bundled schema.")
    p.add_argument("--kind", required=True, choices=sorted(schema_registry().keys()))
    p.add_argument("file", help="JSON artifact path, or - for stdin.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_validate)

    p = sub.add_parser("init", help="Create starter generated CheckYourself files in a target project.")
    p.add_argument("project", nargs="?", default=".")
    p.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(func=command_init)

    p = sub.add_parser("mcp", help="Run the stdio MCP server.")
    p.set_defaults(func=lambda _args: run_mcp_server())
    return parser


def legacy_scan_main(argv: Sequence[str]) -> int:
    parser = CheckYourselfParser(
        prog="checkyourself",
        description="Optional local scan & scaffold for CheckYourself.",
    )
    add_scan_args(parser)
    args = parser.parse_args(list(argv))
    return command_scan(args)


def main(argv: Optional[List[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    commands = {
        "describe",
        "scan",
        "diagnostic",
        "schema",
        "coverage",
        "challenge",
        "receipt",
        "score",
        "backlog",
        "next",
        "diff",
        "validate",
        "init",
        "mcp",
    }
    try:
        if raw and raw[0] in {"-h", "--help"}:
            build_parser().print_help()
            return 0
        if raw and raw[0] not in commands and not raw[0].startswith("-") and not Path(raw[0]).exists():
            # A misspelled command would otherwise be treated as a project
            # path, silently scanning nothing useful.
            import difflib

            close = difflib.get_close_matches(raw[0], sorted(commands), n=1)
            hint = f" Did you mean: {close[0]}?" if close else ""
            raise CliError(f"unknown command or path: {raw[0]}.{hint}")
        if not raw or raw[0] not in commands:
            return legacy_scan_main(raw)
        parser = build_parser()
        args = parser.parse_args(raw)
        return args.func(args)
    except CliError as exc:
        json_requested = any(
            token == "--format=json" or (token == "--format" and index + 1 < len(raw) and raw[index + 1] == "json")
            for index, token in enumerate(raw)
        )
        retry = cli_retry_for(raw[0] if raw else "")
        if json_requested:
            # A shell creates `> output.json` before this process starts. Keep
            # that file parseable when a JSON-mode command fails validation.
            write_json({"error": str(exc), "code": exc.code, "retry": retry})
        print(f"error: {exc}", file=sys.stderr)
        print(retry, file=sys.stderr)
        return exc.code
