#!/usr/bin/env bash
# The floor checks (CR-01–CR-03, CR-08) on the diff since a base: scripts/check.sh floor [--base REF].
exec bash "$(dirname "$0")/check.sh" floor "$@"
