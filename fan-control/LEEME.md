# Control de ventiladores de unix-dashboard

La interfaz y las RPM funcionan sin este servicio. Para aplicar perfiles de velocidad, instala el servicio local con:

```bash
sudo bash fan-control/install.sh
```

Después abre el dashboard y pulsa **T** o **P**. En Ventilación y perfiles, elige los dispositivos y el modo de uso. El servicio inicia en **Automático**, sin seleccionar ningún canal ni alterar el control del firmware.

Los perfiles Silencioso, Equilibrado y Rendimiento tienen puntos editables a 40, 60 y 75 °C; a 85 °C se fuerza el 100%. El conjunto ARCTIC de la placa conserva un mínimo del 50%. No se configura una bomba independiente. No se altera el modo eléctrico PWM/DC.

La lectura activa de la placa es FAN 2 del controlador nct6799. El usuario identifica su ARCTIC conectada a CPU_FAN1; Linux no proporciona una etiqueta física para ese canal. No se selecciona de forma automática.

El servicio vuelve al estado original del firmware al seleccionar Automático, perder comunicación durante 20 segundos, apagarse o encontrar un error. Un registro protegido permite restaurar el estado original incluso si el proceso termina inesperadamente. Se verificaron las protecciones con sensores simulados y se realizó una prueba breve en el equipo real: ARCTIC al 50%, GPU con curva Equilibrado, aumento de RPM y restauración correcta del modo automático del firmware y NVIDIA.

Para desactivar el servicio y restaurar el control anterior:

```bash
sudo systemctl disable --now unix-dashboard-fans.service
```

La instalación también carga `nct6775` al iniciar Linux para conservar las lecturas de la placa tras reiniciar.
