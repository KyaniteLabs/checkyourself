#!/usr/bin/env node
/**
 * checkyourself npm bin — trampoline to the bundled Python CLI (tools/checkyourself.py).
 *
 * Forwards argv and stdio verbatim, so every subcommand works unchanged,
 * including the stdio MCP server: `checkyourself mcp`.
 *
 * Python resolution order: $CHECKYOURSELF_PYTHON, python3, python.
 */
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const pkgRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const script = join(pkgRoot, "tools", "checkyourself.py");

if (process.argv[2] === "--version" || process.argv[2] === "-v") {
  const manifest = JSON.parse(readFileSync(join(pkgRoot, "checkyourself.manifest.json"), "utf8"));
  console.log(manifest.version);
  process.exit(0);
}

const candidates = [process.env.CHECKYOURSELF_PYTHON, "python3", "python"].filter(Boolean);

function run(i) {
  const child = spawn(candidates[i], [script, ...process.argv.slice(2)], { stdio: "inherit" });
  child.on("error", (err) => {
    if (err.code === "ENOENT") {
      if (i + 1 < candidates.length) return run(i + 1);
      console.error(`checkyourself: no Python 3 interpreter found (tried: ${candidates.join(", ")}).`);
      console.error("Install Python 3, or point CHECKYOURSELF_PYTHON at an interpreter.");
      process.exit(1);
    }
    throw err;
  });
  process.on("SIGINT", () => child.kill("SIGINT"));
  process.on("SIGTERM", () => child.kill("SIGTERM"));
  child.on("close", (code, sig) => {
    if (sig) process.kill(process.pid, sig);
    else process.exitCode = code ?? 1;
  });
}

run(0);
