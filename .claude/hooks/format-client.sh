#!/bin/bash
# PostToolUse hook: format the client file Claude just edited or wrote.
# The file path arrives as JSON on stdin; Claude Code sets no $CLAUDE_FILE_PATH variable.

file=$(jq -r '.tool_input.file_path // empty')
client="${CLAUDE_PROJECT_DIR}/client"

# Only client source: Prettier would otherwise reformat docs, data, and config files too.
case "$file" in
  "$client"/src/*.js | "$client"/src/*.vue | "$client"/src/*.css) ;;
  *) exit 0 ;;
esac

# Never fail the tool call over formatting.
cd "$client" && npx --no-install prettier --write "$file" >/dev/null 2>&1 || true
