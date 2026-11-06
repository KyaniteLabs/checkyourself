# Simon's catalog submission — Nov 11 only

Do not run the PR-opening command before Nov 11. Factory has NOT opened a catalog PR. Review gate Nov 9: Product/Kai decide GO using actual exact-head product CI, independent Security approval/merge, validator and the recorded <90s capture. This packet is prepared source; approval/capture are not implied. No new repository, tag, release, npm/PyPI publication or production enablement is authorized here.

1. Using **Simon's personal GitHub login**, confirm `gh auth status` and verify it is the intended personal account, not the factory bot. Use a fresh directory, not the live Hermes checkout.
2. After the product PR is reviewed and merged, execute:

```sh
mkdir -p "$HOME/hackathon-submit/checkyourself-entry"
cd "$HOME/hackathon-submit/checkyourself-entry"
git clone https://github.com/KyaniteLabs/checkyourself.git product
# Confirm the approved immutable plugin object exists:
git -C product cat-file -e d421e421b38168ca8e4e5e4f06dd72c907ace957:hermes-plugin/plugin.yaml
gh repo fork NousResearch/hermes-agent --clone
cd hermes-agent
git switch -c catalog/checkyourself-evidence-gate
cp ../product/catalog/checkyourself-evidence-gate.yaml plugin-catalog/checkyourself-evidence-gate.yaml
```

3. Test the **pinned subtree**, not whatever product main now contains:

```sh
mkdir ../pinned-plugin
git -C ../product archive d421e421b38168ca8e4e5e4f06dd72c907ace957 hermes-plugin | tar -x -C ../pinned-plugin
hermes plugins validate ../pinned-plugin/hermes-plugin --json
# Current catalog admission tests; inspect the latest README/workflows for any additional checks.
python -m pytest tests/hermes_cli/test_plugin_catalog.py
```

If the current catalog test path has changed, use its current documented test, not an invented success. The checked local runtime test file is `tests/hermes_cli/test_plugin_catalog.py`. Attach the saved JSON receipt and real demo/captions to the submission. No optional image URL is present until real banner/screenshots exist.

4. Read the disclosure-first `../product/catalog/PR-BODY.md`, add actual product PR/CI/approval/merge and capture links, remove no caveats, then end the body with `/home/simon/factory/bin/factory-sign --md` output if factory text has changed. Confirm pin/maintainer eligibility and min version against the then-current catalog rules.
5. **Only Simon, on Nov 11:**

```sh
git add plugin-catalog/checkyourself-evidence-gate.yaml
git commit -m "catalog: add Check Yourself Evidence Gate"
git push -u origin catalog/checkyourself-evidence-gate
gh pr create --repo NousResearch/hermes-agent --base main --title "catalog: Check Yourself Evidence Gate" --body-file ../product/catalog/PR-BODY.md
```

Read back the resulting PR and checks with `gh pr view`/`gh pr checks`. Catalog maintainers—not factory—approve and merge. If any prerequisite is missing, postpone; do not fabricate media or approval links.
