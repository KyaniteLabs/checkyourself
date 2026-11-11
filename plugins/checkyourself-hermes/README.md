# CheckYourself for Hermes

An agent that says "done" is making a claim, and the claim is often wrong: the tests never ran, the key is still in the repo, or there is no CI at all. This plugin makes Hermes check before it agrees. It re-derives each claim from the work and scans the project for launch risks. It wraps the CheckYourself v1.7.0 command-line tool.

## What it adds

- **A check-yourself brief.** When a message asks whether work is done or ready to ship ("is it really done?", "can we launch?", "production-ready?"), Hermes adds a short brief. It tells the agent to re-derive each claim from the work, label it CONFIRMED, REFUTED or UNVERIFIABLE with evidence, and treat a scan with no findings as Unknown, not a pass. It is a word-pattern match, tuned so that "are we done with lunch?" or "can we ship the package to Ohio?" don't trigger it, but it can still miss or misfire; turn it off with `inject_on_ship_talk: false`. This is the `pre_llm_call` hook.
- **Two agent tools.**
  - `checkyourself_scan` scans a project folder for launch risks: committed secrets and `.env` files, missing tests or CI, a missing lockfile, debug mode, open CORS, default credentials and risky code patterns. It returns the top 10 findings by severity, how many there are in all, whether the scan was incomplete, and a score estimate. `deep: true` adds the slower CI workflow and supply-chain checks. `path` is relative to the scan root.
  - `checkyourself_next` ranks what to fix first from the last scan, each item with how to verify and roll it back.
- **A slash command.** `/checkyourself scan [folder] [--deep] | next [folder] | status | help` does the same from chat. Quote a folder name with spaces: `/checkyourself scan "my app"`.
- **A skill.** The bundled `checkyourself` skill walks the agent through listing claims, re-deriving them and reporting verdict-first.

## Install

```bash
hermes plugins install checkyourself
hermes plugins enable checkyourself
```

Until the catalog lists it, install from the repository: `hermes plugins install KyaniteLabs/checkyourself/plugins/checkyourself-hermes`. That installs the latest `main`, not a pinned release, so read the commit before you install it. The catalog entry, once listed, pins one reviewed commit.

It needs nothing beyond the Python that runs Hermes.

## What it does on your machine

- **It reads files and nothing else.** The CLI reads files inside the scan root and never runs project code, installs anything or calls the network. The scan root is `scan_root` if you set it, otherwise the session's working folder as Hermes resolves it (the folder pinned for this session, then the profile's terminal folder, then the folder Hermes started in). A path outside it, including one reached through a symlink, is refused before the CLI starts.
- **The CLI is checked before it runs.** The bundled CLI runs with the same Python as Hermes, in isolated mode (`-I`). Before every call the plugin compares each bundled file with `vendor/MANIFEST.json` (SHA-256). A changed or missing file stops the call.
- **No keys reach it.** The CLI gets a minimal environment: PATH, HOME, user, locale and temp folders. It never sees your API keys or tokens.
- **Scans stay in one folder.** The raw JSON of the last 20 scans is kept in `<HERMES_HOME>/plugin-data/checkyourself/scans/`, in a folder only you can read, so `next` can work from the last scan. Nothing else is written. The CLI's own `--no-write` and `--no-history` flags keep reports out of your project.
- **Nothing runs in the background.** There is no telemetry and there are no background jobs. The plugin acts only when its hook matches a message or when you call a tool or the slash command.

## Settings

Set these under `plugins.entries.checkyourself.settings`.

| Key | Default | What it does |
|---|---|---|
| `scan_root` | empty: the session's working folder | Absolute folder that scans may read |
| `inject_on_ship_talk` | `true` (must be `true` or `false`, not a string) | Adds the brief when a message asks whether work is done |
| `allow_slash_scan_on_gateway` | `false` (only a real `true` turns it on) | Allows `/checkyourself scan` and `next` on chat platforms such as Discord |
| `max_files` | `6000` | Most files one scan reads (100 to 50,000) |
| `timeout_seconds` | `120` | Time limit for each CLI call (5 to 900) |

## Known issues

- **No findings is not a pass.** The scan sees only what files show. Runtime behaviour, server-side auth and what is deployed are outside it. The agent is told to say Unknown.
- **The score is an estimate.** Without coverage evidence, the CLI caps its confidence and says so. The plugin passes the number through and never makes one up.
- **Findings can be wrong.** Pattern checks raise false positives, such as a test fixture that looks like a key. Check a finding in the file before you act on it.
- **How it looks is TasteCheck's job.** CheckYourself checks claims and launch risk. Accessibility and how a page actually renders belong to [TasteCheck](https://github.com/KyaniteLabs/tastecheck), which audits the page in a real browser.
- **Chat platforms.** On gateway platforms, `/checkyourself scan` and `next` are refused unless you set `allow_slash_scan_on_gateway: true`. Even then, replies show folder names, never full paths. The agent tools work everywhere.
- **Large folders.** A scan stops after `max_files` and says it was cut short. Raise `max_files` or scan a subfolder to cover more.
- **Platforms.** Tested on Linux only. macOS and Windows are unverified.

License: Apache-2.0, the same as CheckYourself.
