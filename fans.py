"""Read motherboard hwmon fans and NVIDIA fan telemetry without changing controls."""
import ctypes as C
import os
import json
import socket
import time
from pathlib import Path

class FanSpeed(C.Structure):
    _fields_=[('version',C.c_uint),('fan',C.c_uint),('speed',C.c_uint)]

class Monitor:
    def __init__(self):
        self.nvml=None;self.gpu=C.c_void_p();self.last_control=0;self.control={"ready":False,"mode":"Automático","error":"Servicio de control pendiente de instalar"};self.last_signature=None
        try:
            lib=C.CDLL('libnvidia-ml.so.1')
            if lib.nvmlInit_v2()==0 and lib.nvmlDeviceGetHandleByIndex_v2(C.c_uint(0),C.byref(self.gpu))==0:self.nvml=lib
        except (OSError,AttributeError):pass

    def update_control(self,settings):
        signature=json.dumps({k:settings[k] for k in ['fanMode','fanChannels','fanGPU','fanProfiles','fanBoost']},sort_keys=True)
        if signature==self.last_signature and time.monotonic()-self.last_control<5:return
        self.last_control=time.monotonic();self.last_signature=signature
        mode='Rendimiento' if settings['fanBoost'] else settings['fanMode']
        request=dict(mode=mode,channels=settings['fanChannels'],gpu=settings['fanGPU'],curve=[100,100,100,100] if settings['fanBoost'] else settings['fanProfiles'].get(mode,[40,60,85,100]))
        try:
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(0.75);client.connect('/run/unix-dashboard-fans/control.sock');client.sendall(json.dumps(request).encode()+b'\n')
                raw=b''
                while b'\n' not in raw:
                    piece=client.recv(4096)
                    if not piece:break
                    raw+=piece
                    if len(raw)>8192:raise ValueError()
                self.control=json.loads(raw)
        except (OSError,ValueError):self.control=dict(ready=False,mode='Automático',error='Servicio de control pendiente de instalar')

    def snapshot(self):
        rows=[];hwmon_count=0
        for chip in sorted(Path('/sys/class/hwmon').glob('hwmon*')):
            try:name=(chip/'name').read_text().strip()
            except OSError:continue
            for path in sorted(chip.glob('fan*_input')):
                try:
                    index=path.stem.removeprefix('fan').removesuffix('_input')
                    rpm=int(path.read_text());hwmon_count+=1
                    label_path=chip/f'fan{index}_label'
                    label=label_path.read_text().strip() if label_path.exists() else ('ARCTIC · placa FAN 2' if name=='nct6799' and index=='2' else f'{name} · FAN {index}')
                    pwm=chip/f'pwm{index}'
                    rows.append(dict(id=f'{name}:fan{index}',label=label,rpm=rpm,percent=None,source='Placa',controlAvailable=pwm.exists(),writable=os.access(pwm,os.W_OK),status='Detenido' if rpm==0 else 'En marcha'))
                except (OSError,ValueError):continue
        if self.nvml:
            try:
                count=C.c_uint()
                if self.nvml.nvmlDeviceGetNumFans(self.gpu,C.byref(count))==0:
                    for i in range(min(count.value,12)):
                        percent=C.c_uint();pct=None;rpm=None
                        if self.nvml.nvmlDeviceGetFanSpeed_v2(self.gpu,C.c_uint(i),C.byref(percent))==0:pct=percent.value
                        speed=FanSpeed(C.sizeof(FanSpeed)|(1<<24),i,0)
                        if self.nvml.nvmlDeviceGetFanSpeedRPM(self.gpu,C.byref(speed))==0:rpm=speed.speed
                        if rpm is not None or pct is not None:
                            rows.append(dict(id=f'nvidia:{i}',label=f'GPU · ventilador {i+1}',rpm=rpm,percent=pct,source='NVIDIA',controlAvailable=True,writable=False,status='Automático NVIDIA'))
            except AttributeError:pass
        return dict(rows=rows,motherboardDetected=hwmon_count>0,controlReady=self.control.get('ready',False),control=self.control,status=self.control.get('mode','Automático'),detail='CPU y chasis: controlador de sensores pendiente' if not hwmon_count else 'Lecturas de placa disponibles; control por perfiles pendiente de habilitar')
