# Desarrollo
Este directorio es la fuente del proyecto. La instalación activa está en
`~/.config/unix-dashboard`; no confundir ambas copias.

- Trabajar aquí y usar `./install.sh` para desplegar cuando corresponda.
- Conservar preferencias, historial SQLite y asignaciones físicas del usuario.
- No ejecutar pruebas que cambien PWM o iluminación como comprobación automática.
- Las pruebas QML deben ejecutarse con backend software y sin servicios reales.
- No versionar bases de datos, ajustes personales, dependencias descargadas ni binarios.
- Los dispositivos RGB y la geometría/monitor están adaptados actualmente a un equipo
  concreto; documentar esa limitación antes de generalizar soporte.
- No asignar canales de ventiladores automáticamente. La bomba requiere tratamiento específico.
