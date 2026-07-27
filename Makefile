# The GitHub Pages demos are generator output committed to the repo. The exact
# invocation used to live nowhere, so they drifted: both pages shipped for weeks
# without the DOMPurify sanitize fix that had already landed in the generator.
# Pinning the command here — and diffing it in CI — is what stops that recurring.
PAGES_LINK := https://github.com/scaccogatto/okf-skills
PAGES_OG   := https://scaccogatto.github.io/okf-skills/assets/og.png
VISUALIZE  := uv run skills/visualize/scripts/okf_visualize.py

.PHONY: docs test validate

docs:
	$(VISUALIZE) examples/sample-bundle -o docs/index.html \
	  --title "Storefront · a live OKF bundle" \
	  --link "$(PAGES_LINK)" --og-image "$(PAGES_OG)" --layout breadthfirst
	$(VISUALIZE) .okf -o docs/self.html \
	  --title "okf-skills · documented in its own format" \
	  --link "$(PAGES_LINK)" --og-image "$(PAGES_OG)" --layout breadthfirst

test:
	uv run tests/test_okf_validate.py

validate:
	uv run skills/validate/scripts/okf_validate.py examples/sample-bundle --strict
	uv run skills/validate/scripts/okf_validate.py .okf --strict
