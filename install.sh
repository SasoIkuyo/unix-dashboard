#!/usr/bin/env bash
# Install user files; does not install the privileged fan service or change hardware.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "$0")" && pwd)"
install_root="$HOME/.config/unix-dashboard"
python3 -m pip --version >/dev/null
bash "$project_root/native/build.sh"
mkdir -p "$install_root/native" "$install_root/vendor" "$HOME/.config/systemd/user" "$HOME/.local/bin"
# Preserve existing preferences, usage database, weather and hardware mappings.
for pattern in '*.py' '*.qml' '*.sh' '*.conf' '*.jsonc'; do
    find "$project_root" -maxdepth 1 -type f -name "$pattern" -exec cp -t "$install_root" -- {} +
done
cp -R "$project_root/pc3d" "$install_root/"
cp "$project_root/native/main.cpp" "$project_root/native/build.sh" "$project_root/native/dashboard-native" "$install_root/native/"
python3 -m pip install --target "$install_root/vendor" --upgrade -r "$project_root/requirements.txt"
if [ ! -f "$install_root/appearance.json" ]; then
    cp "$project_root/appearance.example.json" "$install_root/appearance.json"
fi
python3 - "$install_root" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
for name in ['session.conf','btop.conf']:
    p=root/name;p.write_text(p.read_text().replace('@CONFIG_DIR@',str(root)))
PY
install -m 0755 "$project_root/scripts/wallpaper-pause.py" "$HOME/.local/bin/game-wallpaper-pause"
cp "$project_root/systemd/"*.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
python3 "$install_root/palette.py"
echo 'Instalado. Ejecuta ~/.config/unix-dashboard/start.sh para abrirlo.'
echo 'El servicio de ventiladores se instala por separado y requiere sudo.'
