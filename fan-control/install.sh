#!/usr/bin/env bash
set -euo pipefail
if [ "$(id -u)" != 0 ] || [ -z "${SUDO_USER:-}" ]; then
    echo 'Ejecuta: sudo bash install.sh' >&2
    exit 1
fi
fan_user="$SUDO_USER"
fan_uid="$(id -u "$fan_user")"
fan_source="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 -m py_compile "$fan_source/fan-service.py"
modprobe nct6775
install -d -m 0755 /usr/local/lib/unix-dashboard
install -o root -g root -m 0755 "$fan_source/fan-service.py" /usr/local/lib/unix-dashboard/fan-service.py
cat > /etc/systemd/system/unix-dashboard-fans.service <<EOF
[Unit]
Description=Unix Dashboard fan profiles
After=multi-user.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/lib/unix-dashboard/fan-service.py --uid=$fan_uid
ExecStopPost=/usr/bin/python3 /usr/local/lib/unix-dashboard/fan-service.py --uid=$fan_uid --restore-only
RuntimeDirectory=unix-dashboard-fans
RuntimeDirectoryMode=0755
Restart=on-failure
RestartSec=3
TimeoutStopSec=8
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=full
[Install]
WantedBy=multi-user.target
EOF
printf 'nct6775\n' > /etc/modules-load.d/unix-dashboard-fans.conf
systemctl daemon-reload
systemctl enable unix-dashboard-fans.service
systemctl restart unix-dashboard-fans.service
echo 'Control de ventiladores habilitado. El modo inicial es Automático; no se asigna ningún canal de placa automáticamente.'
