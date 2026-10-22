#!/usr/bin/env python3
"""Privileged fan controller. Fixed hwmon allowlist; local user only; 20s lease.

Never selects a motherboard channel automatically. Firmware state is restored on
lease expiration, disconnect, error, Automatic mode, shutdown, or SIGTERM.
"""
import argparse
import ctypes as C
import json
import math
import os
from pathlib import Path
import signal
import socket
import struct
import threading
import time

TEMPS=[40,60,75,85]
SUPPORTED={'nct6799','nct6796','nct6798','nct6779'}
RECOVERY=Path('/run/unix-dashboard-fans/recovery.json')

def interpolate(curve,temp):
    if not math.isfinite(temp) or temp>=85:return 100
    if temp<=40:return curve[0]
    for i in range(1,4):
        if temp<=TEMPS[i]:return round(curve[i-1]+(curve[i]-curve[i-1])*(temp-TEMPS[i-1])/(TEMPS[i]-TEMPS[i-1]))
    return 100

def validate(request):
    mode=request.get('mode','Automático')
    channels=request.get('channels',[])
    gpu=request.get('gpu',False)
    curve=request.get('curve',[40,60,85,100])
    if mode not in ('Automático','Silencioso','Equilibrado','Rendimiento'):raise ValueError('Modo no válido')
    if not isinstance(channels,list) or any(type(i) is not int or not 1<=i<=7 for i in channels) or len(channels)!=len(set(channels)):raise ValueError('Canales no válidos')
    if type(gpu) is not bool:raise ValueError('GPU no válida')
    if not isinstance(curve,list) or len(curve)!=4 or any(type(v) is not int or not 30<=v<=100 for v in curve) or sorted(curve)!=curve or curve[-1]!=100:raise ValueError('Curva no válida')
    if mode!='Automático' and not (channels or gpu):raise ValueError('No hay ventiladores seleccionados')
    return dict(mode=mode,channels=channels,gpu=gpu,curve=curve)

class Controller:
    def __init__(self):
        self.request=validate({});self.updated=0;self.lock=threading.RLock();self.stop=threading.Event();self.original={};self.gpu_active=False;self.error='';self.targets={};self.activation={}
        self.nvml=None;self.device=C.c_void_p()
        try:
            lib=C.CDLL('libnvidia-ml.so.1')
            if lib.nvmlInit_v2()==0 and lib.nvmlDeviceGetHandleByIndex_v2(C.c_uint(0),C.byref(self.device))==0:self.nvml=lib
        except (OSError,AttributeError):pass
    def chip(self):
        for p in Path('/sys/class/hwmon').glob('hwmon*'):
            try:
                if (p/'name').read_text().strip() in SUPPORTED:return p
            except OSError:pass
        raise ValueError('Controlador de placa no encontrado')
    def temperature(self):
        values=[]
        for p in Path('/sys/class/hwmon').glob('hwmon*'):
            try:
                if (p/'name').read_text().strip()!='k10temp':continue
                for f in p.glob('temp*_input'):values.append(int(f.read_text())/1000)
            except (OSError,ValueError):pass
        return max(values) if values else 100
    def gpu_fans(self):
        if not self.nvml:raise ValueError('NVIDIA no disponible')
        count=C.c_uint()
        if self.nvml.nvmlDeviceGetNumFans(self.device,C.byref(count))!=0:raise ValueError('Lectura de GPU no disponible')
        return range(min(count.value,12))
    def journal(self):
        records={key:dict(pwm=int(value[2]),enable=int(value[3])) for key,value in self.original.items()}
        temp=RECOVERY.with_suffix('.tmp');temp.write_text(json.dumps(dict(channels=records,gpu=self.gpu_active)));temp.chmod(0o600);temp.replace(RECOVERY)
    def recover(self):
        try:record=json.loads(RECOVERY.read_text())
        except (OSError,ValueError):return
        if record.get('channels'):
            chip=self.chip()
            for key,values in record['channels'].items():
                if key not in [str(i) for i in range(1,8)]:continue
                pwm=values.get('pwm');enable=values.get('enable')
                if type(pwm) is int and 0<=pwm<=255 and type(enable) is int and 0<=enable<=5:
                    self.original[key]=(chip/f'pwm{key}',chip/f'pwm{key}_enable',str(pwm),str(enable))
        self.gpu_active=bool(record.get('gpu'))
        self.restore()
    def restore(self,keep=()):
        for key in list(self.original):
            if key in keep:continue
            pwm,enable,old_pwm,old_enable=self.original[key]
            try:
                if old_enable.strip()=='1':
                    enable.write_text('1');pwm.write_text(old_pwm)
                else:
                    # Automatic modes own the PWM register; writing it returns EBUSY.
                    enable.write_text(old_enable)
                del self.original[key];self.activation.pop(key,None)
            except OSError as exc:self.error='No se pudo restaurar '+key+': '+str(exc)
        if self.gpu_active and 'gpu' not in keep:
            try:
                errors=[self.nvml.nvmlDeviceSetDefaultFanSpeed_v2(self.device,C.c_uint(i)) for i in self.gpu_fans()]
                if any(errors):raise ValueError('No se pudo restaurar GPU')
                self.gpu_active=False
            except Exception as exc:self.error=str(exc)
        self.targets={}
        self.journal()
    def accept(self,request):
        values=validate(request)
        with self.lock:
            if values['mode']!='Automático':
                if values['channels']:
                    chip=self.chip()
                    for i in values['channels']:
                        # A pump must never be chosen by automated channel discovery.
                        rpm=int((chip/f'fan{i}_input').read_text())
                        if rpm<=0:raise ValueError(f'FAN {i} no reporta giro; no se aplicará control')
                        if not (chip/f'pwm{i}_enable').exists():raise ValueError('Canal sin control PWM')
                if values['gpu']:list(self.gpu_fans())
            self.request=values;self.updated=time.monotonic();self.error=''
            self.apply()
            return self.status()
    def status(self):
        return dict(ready=True,mode=self.request['mode'],error=self.error,targets=self.targets,active=bool(self.original or self.gpu_active))
    def apply(self):
        r=self.request
        if r['mode']=='Automático' or time.monotonic()-self.updated>20:
            self.restore();self.request=validate({});return
        keep={str(i) for i in r['channels']}
        if r['gpu']:keep.add('gpu')
        self.restore(keep)
        if r['channels']:
            chip=self.chip();speed=max(50,interpolate(r['curve'],self.temperature()))
            for i in r['channels']:
                key=str(i);pwm=chip/f'pwm{i}';enable=chip/f'pwm{i}_enable'
                if key not in self.original:
                    self.original[key]=(pwm,enable,pwm.read_text(),enable.read_text());self.activation[key]=time.monotonic();self.journal()
                target=speed
                if time.monotonic()-self.activation[key]>10 and int((chip/f'fan{i}_input').read_text())<=0:target=100;self.error=f'FAN {i} sin giro: velocidad forzada a 100%'
                enable.write_text('1');pwm.write_text(str(round(target*255/100)));self.targets[key]=target
        if r['gpu']:
            temp=C.c_uint();speed=100
            if self.nvml.nvmlDeviceGetTemperature(self.device,C.c_uint(0),C.byref(temp))==0:speed=interpolate(r['curve'],temp.value)
            self.gpu_active=True;self.journal()
            for i in self.gpu_fans():
                rc=self.nvml.nvmlDeviceSetFanSpeed_v2(self.device,C.c_uint(i),C.c_uint(speed))
                if rc:raise ValueError('El controlador NVIDIA rechazó el control (código '+str(rc)+')')
            self.targets['gpu']=speed
    def run(self):
        while not self.stop.wait(2):
            with self.lock:
                try:self.apply()
                except Exception as exc:
                    self.error=str(exc);self.request=validate({});self.restore()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--uid',type=int,required=True);parser.add_argument('--restore-only',action='store_true');args=parser.parse_args()
    path='/run/unix-dashboard-fans/control.sock'
    controller=Controller();controller.recover()
    if args.restore_only:return
    threading.Thread(target=controller.run,daemon=True).start()
    signal.signal(signal.SIGTERM,lambda *_:controller.stop.set());signal.signal(signal.SIGINT,lambda *_:controller.stop.set())
    with socket.socket(socket.AF_UNIX) as server:
        try:os.unlink(path)
        except FileNotFoundError:pass
        server.bind(path);os.chown(path,args.uid,-1);os.chmod(path,0o600);server.listen(4);server.settimeout(1)
        try:
            while not controller.stop.is_set():
                try:conn,_=server.accept()
                except socket.timeout:continue
                with conn:
                    conn.settimeout(2)
                    _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    if uid not in (0,args.uid):continue
                    try:
                        raw=b''
                        while b'\n' not in raw:
                            raw+=conn.recv(4096)
                            if len(raw)>4096 or not raw:raise ValueError('Requête no válida')
                        request=json.loads(raw.split(b'\n')[0])
                        with controller.lock:
                            if request.get('action')=='status':result=controller.status()
                            else:result=controller.accept(request)
                    except Exception as exc:
                        with controller.lock:
                            controller.request=validate({});controller.restore();controller.error=str(exc);result=controller.status()
                    try:conn.sendall(json.dumps(result).encode()+b'\n')
                    except OSError:pass
        finally:
            with controller.lock:controller.restore()
            os.unlink(path)
if __name__=='__main__':main()
