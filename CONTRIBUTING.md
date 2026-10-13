# Contributing

Issues and pull requests are welcome. CI enforces a few rules on every PR, and
they are listed here so you meet them before a red check does.

## The three PR gates (`version-bump` check)

1. **Version bump.** A PR that changes the shipped surface (`.claude-plugin/`,
   `skills/`, `agents/`, `hooks/`, `servers/`, `templates/`, `action.yml`,
   `.mcp.json`) must raise `version` in `.claude-plugin/plugin.json` above the
   version on `main`. Merging the bump tags `okf--v<version>` and publishes the
   release automatically, so rebase and pick the next free number if `main`
   moved while your PR was open.
2. **Changelog entry.** A version bump needs a `## [<version>] - YYYY-MM-DD`
   section in `CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)).
   That section becomes the GitHub release notes, so write it for users.
3. **Bundle upkeep.** A change under `skills/*/scripts/`, `agents/` or `hooks/`
   must also update the concept that describes it under `.okf/`. Locally, the
   plugin's Stop hook enforces the same rule (`OKF_HOOK=off` opts out).

The `skip-version-check` label bypasses all three, for a PR that genuinely
ships nothing. Dependabot PRs that only bump the `action.yml` pin are exempt
from the version bump and ship with the next release.

## Checks to run locally

Everything runs with [uv](https://docs.astral.sh/uv/), no virtualenv needed:

```sh
make lint      # ruff, pinned to the version CI uses
make test      # every unit and end-to-end suite
make validate  # both bundles, --strict
make docs      # regenerate docs/*.html; CI fails if the committed pages differ
```

## Dependencies

The scripts are [PEP 723](https://peps.python.org/pep-0723/) inline-metadata
scripts. Dependabot cannot read them, so dependency bounds (`mcp>=2,<3`,
`pyyaml>=6,<7`) are bumped by hand. The visualizer's CDN scripts are pinned to
an exact version with Subresource Integrity: a bump means recomputing the hash
and running `make docs`. `tests/test_supply_chain.py` enforces both.

## Security

Do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
