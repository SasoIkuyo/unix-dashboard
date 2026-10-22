#!/usr/bin/env bash
# Arranca una única instancia del tracker de presencia/uso.
set -u
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/unix-dashboard-tracker.lock"
flock -n 9 || exit 0
exec python3 "$HOME/.config/unix-dashboard/tracker.py"
