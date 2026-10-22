#!/usr/bin/env python3
"""Native Qt Quick dashboard; reads the existing sampler and usage database."""
import calendar
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dashboard import Sampler, Usage, fmt_dur, MESES, DIAS, DIAS_CORTOS
import icons
import weather
import preferences
import fans
import lighting

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / 'appearance.json'
THEMES = preferences.THEMES
state = {}
lock = threading.Lock()
stop = threading.Event()

def collect():
    sampler, usage = Sampler(), Usage()
    fan_monitor=fans.Monitor()
    while not stop.is_set():
        try:
            sampler.update()
            usage.refresh()
            now = dt.datetime.now()
            days = []
            for week in calendar.Calendar().monthdatescalendar(now.year, now.month):
                for date in week:
                    seconds = usage.seconds_for(date)
                    days.append(dict(day=date.day, current=date.month == now.month, today=date == now.date(), value=seconds, duration=fmt_dur(seconds)))
            settings = preferences.load()
            fan_monitor.update_control(settings)
            import theme
            palette = theme.load()
            data = dict(clock=now.strftime('%H:%M'), seconds=now.strftime('%S'), date=f'{DIAS[now.weekday()].upper()} · {now.day} {MESES[now.month-1].upper()} {now.year}', month=f'{MESES[now.month-1].capitalize()} {now.year}', week=now.isocalendar().week, weekday=now.weekday(), weekDates=[(now.date()-dt.timedelta(days=now.weekday())+dt.timedelta(days=i)).day for i in range(7)], day=now.day, monthDays=calendar.monthrange(now.year, now.month)[1], host=sampler.host, kernel=sampler.kernel,
                gauges=[dict(label='CPU', value=sampler.cpu_pct, text=f'{sampler.cpu_pct:.0f}%', detail=f'{os.cpu_count()} hilos · {sampler.load[0]:.1f} load'), dict(label='MEMORIA', value=sampler.ram_pct, text=f'{sampler.ram_pct:.0f}%', detail=f'{(sampler.ram_total_kib-sampler.ram_avail_kib)/1048576:.1f} / {sampler.ram_total_kib/1048576:.0f} GiB'), dict(label='GPU', value=sampler.gpu_pct, text=f'{sampler.gpu_pct:.0f}%', detail=sampler.gpu_name), dict(label='FREC. MEDIA', value=min(100,sampler.freq_avg/max(1,sampler.freq_max)*100), text=f'{sampler.freq_avg:.2f}', detail='GHz · máx. '+f'{sampler.freq_max:.2f}')],
                therms=[dict(label=r['zone'] if 'zone' in r else r.get('group','').upper(), sensor=r.get('label',''), value=r['temp'], low=sampler.therm_minmax[r['key']][0], high=sampler.therm_minmax[r['key']][1]) for r in sampler.therms], cpuHistory=sampler.cpu_temp_hist[-90:], gpuHistory=sampler.gpu_temp_hist[-90:], days=days,
                uptime=fmt_dur(sampler.uptime), session=fmt_dur((now-usage.session_start).total_seconds()) if usage.session_start else '—', today=fmt_dur(usage.seconds_for(now.date())), total=fmt_dur(usage.month_total(now)), streak=usage.streak(now), activeDays=usage.month_active_days(now), weekDays=[dict(label=DIAS_CORTOS[d.weekday()]+' '+str(d.day), seconds=s, duration=fmt_dur(s)) for d,s in usage.last_days(now,7)], apps=[dict(name=icons.display_name(c), seconds=s, duration=fmt_dur(s)) for c,s in usage.apps[:6]], theme=settings.get('theme','Lavanda'), systemPalette=[palette['bg'], palette['panel'], palette['accent'], palette['fg'],palette['dim'],palette['gpu']])
            month_total = usage.month_total(now)
            active_days = usage.month_active_days(now)
            registered = sum(seconds for _, seconds in usage.apps)
            presence = usage.seconds_for(now.date())
            best_date, best_seconds = usage.best_day(now)
            history = usage.last_days(now, 30)
            data.update(
                weather=weather.snapshot(), preferences=settings, fans=fan_monitor.snapshot(), lighting=lighting.snapshot(),
                monthAverage=fmt_dur(month_total / max(1, active_days)),
                bestDay=(str(best_date.day) + ' (' + fmt_dur(best_seconds) + ')') if best_date else '—',
                yearProgress=f'{now.timetuple().tm_yday / (366 if calendar.isleap(now.year) else 365) * 100:.1f}%',
                history30=[seconds for _, seconds in history],
                historyMaximum=fmt_dur(max((seconds for _, seconds in history), default=0)),
                historyAverage=fmt_dur(sum(seconds for _, seconds in history) / 30),
                cpuName=sampler.cpu_name,
                ramTotal=f'{sampler.ram_total_kib / 1048576:.0f} GiB',
                thermalMinimum=f'{min((v[0] for v in sampler.therm_minmax.values()), default=0):.1f}°C',
                thermalMaximum=f'{max((v[1] for v in sampler.therm_minmax.values()), default=0):.1f}°C',
                registered=fmt_dur(registered), idle=fmt_dur(max(0, presence-registered)),
                appCount=len(usage.apps),
                appsWeek=[dict(name=icons.display_name(c), icon=icons.icon_for(c), iconName=icons.native_icon(c), seconds=seconds, duration=fmt_dur(seconds)) for c,seconds in usage.apps_week[:6]],
            )
            for item, (cls, _) in zip(data['apps'], usage.apps):
                item['icon'] = icons.icon_for(cls)
                item['iconName'] = icons.native_icon(cls)
            if sampler.gpu_mem_total:
                data['gauges'][2]['detail'] += f' · VRAM {sampler.gpu_mem_used/1024:.1f}/{sampler.gpu_mem_total/1024:.1f} GiB'
            with lock:
                state.clear(); state.update(data)
        except Exception as exc:
            print(f'Dashboard update: {exc}', flush=True)
        stop.wait(preferences.load()["refreshInterval"]/1000)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path != '/state':
            self.send_error(404); return
        with lock: body = json.dumps(state).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            self.send_error(403);return
        if self.path == '/lighting':
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1024: raise ValueError('Solicitud no válida')
                result=lighting.apply(json.loads(self.rfile.read(size)))
                with lock: state['lighting']=result
                body=json.dumps(result).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
            except (ValueError,TypeError,AttributeError) as exc:
                self.send_error(400,str(exc))
            except (OSError,subprocess.SubprocessError):
                self.send_error(503,'OpenRGB no pudo aplicar la iluminación')
            return
        if self.path == '/weather':
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0 < size <= 1024: raise ValueError()
                weather.set_city(json.loads(self.rfile.read(size))['city'])
                self.send_response(204); self.end_headers()
            except (ValueError,KeyError,TypeError): self.send_error(400)
            return
        if self.path not in ('/theme','/settings'): self.send_error(404); return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=4096:raise ValueError('Tamaño no válido')
            changes=json.loads(self.rfile.read(size))
            if self.path=='/theme':changes={'theme':changes['theme']}
            candidate=preferences.validate({**preferences.load(),**changes})
            if (candidate['fanMode']!='Automático' or candidate['fanBoost']) and not Path('/run/unix-dashboard-fans/control.sock').exists():
                raise ValueError('Instala primero el servicio de control de ventiladores')
            values=preferences.save(changes)
            with lock: state.update(theme=values['theme'],preferences=values)
            if self.path=='/settings':weather.wake.set()
            body=json.dumps(values,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
        except (ValueError,KeyError,TypeError) as exc:
            self.send_error(400,str(exc))

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    threading.Thread(target=collect,daemon=True).start()
    threading.Thread(target=lighting.worker,args=(stop,),daemon=True).start()
    threading.Thread(target=weather.worker,args=(stop,),daemon=True).start()
    try:
        return subprocess.call([str(ROOT/'native/dashboard-native'),'--',str(server.server_port)])
    finally:
        stop.set(); server.shutdown(); server.server_close()
if __name__ == '__main__': raise SystemExit(main())
