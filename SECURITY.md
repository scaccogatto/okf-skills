# Security policy

## Supported versions

Only the latest release (the `okf--v*` tag that the floating `v1` tag points
to) receives fixes. The plugin is pre-1.0, so there are no maintenance branches.

## Reporting a vulnerability

Report it privately through GitHub:
[Report a vulnerability](https://github.com/scaccogatto/okf-skills/security/advisories/new).
Please do not open a public issue or PR for it.

Include the affected component (a skill script, the MCP server, the Stop hook,
the GitHub Action or the generated `viz.html`), the version, and a minimal
bundle or input that reproduces it. A fix ships as a normal release, and the
advisory is published once it is out.

## Scope notes

- Bundle content is treated as untrusted: the visualizer sanitizes rendered
  markdown with DOMPurify and loads its CDN scripts with Subresource Integrity,
  and the MCP server refuses paths that resolve outside the bundle.
- The GitHub Action passes its inputs through environment variables, never
  through `${{ }}` interpolation in shell.
