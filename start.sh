#!/usr/bin/env bash
# Lanza el tablero unixporn en la pantalla izquierda.
# Variables opcionales:
#   DASH_MONITOR=DP-5   fuerza un monitor
#   DASH_FULLSCREEN=1   abre a pantalla completa (por defecto, flotante)
#   start.sh --save     guarda la geometría actual como predeterminada
set -eu

runtime="${XDG_RUNTIME_DIR:-/tmp}"
root="$HOME/.config/unix-dashboard"
DASH_FULLSCREEN="${DASH_FULLSCREEN:-0}"

if [ "${1:-}" = "--save" ]; then
    exec python3 "$root/layout.py" save
fi

# El tracker debe seguir vivo aunque se cierre el tablero.
if ! systemctl --user is-active --quiet unix-dashboard-tracker.service; then
    systemd-run --user --collect --unit=unix-dashboard-tracker "$root/tracker.sh" >/dev/null 2>&1
fi

exec 9>"$runtime/unix-dashboard.lock"
flock -n 9 || exit 0

if hyprctl clients -j 2>/dev/null | python3 -c '
import json, sys
try:
    clients = json.load(sys.stdin)
except Exception:
    clients = []
sys.exit(0 if any((w.get("class") == "unixporn-board" or w.get("title") == "ARCH // WORKSTATION") for w in clients) else 1)
'; then
    exit 0
fi

# El monitor más a la izquierda (o el indicado en DASH_MONITOR).
leftmost_monitor() {
    hyprctl monitors -j 2>/dev/null | python3 -c '
import json, sys
try:
    monitors = json.load(sys.stdin)
except Exception:
    monitors = []
if monitors:
    print(min(monitors, key=lambda m: (m.get("x", 0), m.get("y", 0)))["name"])
' 2>/dev/null || true
}

monitor_exists() {
    hyprctl monitors -j 2>/dev/null | python3 -c '
import json, sys
name = sys.argv[1]
try:
    monitors = json.load(sys.stdin)
except Exception:
    monitors = []
sys.exit(0 if any(m.get("name") == name for m in monitors) else 1)
' "$1" 2>/dev/null
}

monitor_count() {
    hyprctl monitors -j 2>/dev/null | python3 -c '
import json, sys
try:
    print(len(json.load(sys.stdin)))
except Exception:
    print(0)
' 2>/dev/null || echo 0
}

# Al iniciar Hyprland las pantallas pueden tardar un instante en enumerarse.
# Si no se fuerza monitor, espera a tener las dos para elegir bien la izquierda.
if [ -z "${DASH_MONITOR:-}" ]; then
    for _ in $(seq 1 30); do
        [ "$(monitor_count)" -ge 2 ] && break
        sleep 0.1
    done
fi

monitor="${DASH_MONITOR:-}"
if [ -n "$monitor" ] && ! monitor_exists "$monitor"; then
    monitor=""
fi
if [ -z "$monitor" ]; then
    monitor="$(leftmost_monitor)"
fi

python3 "$root/palette.py" >/dev/null 2>&1 || true

# Abre kitty ya con el tamaño guardado para que el primer frame sea el bueno.
initial_size="$(python3 - "$root/layout.json" <<'PY'
import json
import sys
try:
    data = json.load(open(sys.argv[1]))
    width, height = int(data.get("width") or 0), int(data.get("height") or 0)
except Exception:
    width = height = 0
if width > 0 and height > 0:
    print(width, height)
PY
)"

kitty_size=()
if [ -n "$initial_size" ]; then
    read -r initial_w initial_h <<<"$initial_size"
    kitty_size=(-o "initial_window_width=$initial_w" -o "initial_window_height=$initial_h")
fi

if [ "${DASH_UI:-desktop}" = "terminal" ]; then
nohup kitty \
    "${kitty_size[@]}" \
    --config "$root/board.conf" \
    --class unixporn-board \
    --title 'ARCH // WORKSTATION' \
    python3 "$root/dashboard.py" \
    </dev/null >"$runtime/unix-dashboard.log" 2>&1 9>&- &

else
    systemd-run --user --collect --unit=unix-dashboard-desktop \
        --property=Restart=on-failure \
        python3 "$root/desktop.py" >"$runtime/unix-dashboard.log" 2>&1
fi

# Espera a que aparezca el tablero antes de colocar la ventana.
for _ in $(seq 1 50); do
    if hyprctl clients -j 2>/dev/null | grep -Eq '"(class|title)": "(unixporn-board|ARCH // WORKSTATION)"'; then
        break
    fi
    sleep 0.1
done

# Por defecto: ventana flotante con la geometría guardada en layout.json.
# Con DASH_FULLSCREEN=1 se coloca en el monitor y se maximiza.
if [ "$DASH_FULLSCREEN" != "1" ]; then
    if [ -n "$monitor" ]; then
        python3 "$root/layout.py" apply --monitor "$monitor" >>"$runtime/unix-dashboard.log" 2>&1 || true
    else
        python3 "$root/layout.py" apply >>"$runtime/unix-dashboard.log" 2>&1 || true
    fi
elif [ -n "$monitor" ]; then
    board_ok() {
        python3 - "$monitor" <<'PY'
import json
import subprocess
import sys

name = sys.argv[1]
monitors = json.loads(
    subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True).stdout
    or "[]"
)
monitor_id = next((m["id"] for m in monitors if m.get("name") == name), None)
clients = json.loads(
    subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True).stdout
    or "[]"
)
for window in clients:
    if window.get("class") != "unixporn-board" and window.get("title") != "ARCH // WORKSTATION":
        continue
    placed = window.get("monitor") == monitor_id
    full = window.get("fullscreen") == 2
    sys.exit(0 if placed and full else 1)
sys.exit(1)
PY
    }

    for _ in $(seq 1 25); do
        board_ok && break
        hyprctl dispatch 'hl.dsp.focus({ window = "title:^(ARCH // WORKSTATION)$" })' >/dev/null 2>&1 || true
        hyprctl dispatch "hl.dsp.window.move({ monitor = \"$monitor\" })" >/dev/null 2>&1 || true
        hyprctl dispatch 'hl.dsp.window.fullscreen({ mode = "fullscreen" })' >/dev/null 2>&1 || true
        sleep 0.15
    done
fi
