# Security Policy

CheckYourself is local-first and does not run a hosted service, but security
reports still matter because the tool handles project context and may inspect
files that contain sensitive signals.

## Supported Versions

| Track | Support status | Meaning |
|---|---|---|
| Tagged `1.7.x` release line | Supported | The latest tagged release is `1.7.0`; security fixes target this line. |
| Public `main` branch | Supported | The current development branch receives fixes and may change between releases. |
| Tags older than `1.7.0` | Unsupported | Upgrade to the supported release line before requesting a security fix. |

## Reporting A Vulnerability

Please do not post real secrets, private customer data, or exploit details in a
public issue.

For now, report security concerns through the GitHub repository by opening an
issue with a redacted summary and marking it clearly as security-sensitive. If
GitHub private vulnerability reporting is enabled for the repo, use that path
instead.

Include:

- what file, command, or workflow is affected;
- why it could expose data, secrets, or unsafe behavior;
- a redacted reproduction;
- the CheckYourself version or commit tested;
- the safest suggested fix, if known.

## Response Promise

Security reports should be triaged before normal feature requests.

The maintainer should:

1. acknowledge the report;
2. reproduce or request the smallest missing evidence;
3. patch the issue in the smallest reversible change;
4. add or update a test when possible;
5. note the fix in the changelog.

## Secret Handling

CheckYourself output must never include live secret values. If you find a path
that prints credentials, treat it as a P0/P1 issue and redact the evidence in
the report.
