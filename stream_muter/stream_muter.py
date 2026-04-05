"""
StreamMuter - Hotkey para mutear apps específicas sin afectar el sistema.
Compatible con OBS WebSocket v5.
API HTTP + WebSocket en localhost:6767
"""

import sys
import os
import json
import threading
import time
import ctypes
from ctypes import cast, POINTER
from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncio
import websockets

# ─── Notificaciones (win10toast) ──────────────────────────────────────────
try:
    from win10toast import ToastNotifier
    toaster = ToastNotifier()
except ImportError:
    toaster = None

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(app_dir, "config.json")
API_PORT    = 6767

DEFAULT_CONFIG = {
    "hotkey_obs": "f9",
    "hotkey_pc": "f10",
    "apps": [
        "Spotify.exe",
        "VALORANT-Win64-Shipping.exe"
    ],
    "obs": {
        "enabled": False,
        "host": "localhost",
        "port": 4455,
        "password": "",
        "sources_to_mute": []
    },
    "show_tray": False,
    "notify_on_toggle": False,
    "mixer_hotkeys": {},
    "open_browser": True
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    else:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"[StreamMuter] config.json creado.")
        return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ─── AUDIO (pycaw) ──────────────────────────────────────────────────────────
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioMeterInformation
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    print("[StreamMuter] ADVERTENCIA: pycaw no instalado.")


def get_sessions_for_app(exe_name: str):
    if not PYCAW_AVAILABLE:
        return []
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass
    sessions = AudioUtilities.GetAllSessions()
    return [s for s in sessions if s.Process and s.Process.name().lower() == exe_name.lower()]


def set_app_mute(exe_name: str, mute: bool):
    sessions = get_sessions_for_app(exe_name)
    if not sessions:
        return
    for session in sessions:
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMute(mute, None)


# ─── OBS WEBSOCKET ──────────────────────────────────────────────────────────
try:
    import obsws_python as obs
    import logging
    # Suppress OBS websocket internal error prints for non-audio sources parsing
    logging.getLogger("obsws_python").setLevel(logging.CRITICAL)
    OBS_AVAILABLE = True
except ImportError:
    OBS_AVAILABLE = False


class OBSController:
    def __init__(self, host, port, password):
        self.host = host; self.port = port; self.password = password
        self.client = None

    def connect(self):
        if not OBS_AVAILABLE:
            print("[OBS] obsws-python no instalado.")
            return False
        try:
            self.client = obs.ReqClient(host=self.host, port=self.port,
                                        password=self.password, timeout=3)
            print(f"[OBS] Conectado a {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[OBS] No se pudo conectar: {e}")
            self.client = None
            return False

    def set_source_mute(self, source_name: str, mute: bool):
        if not self.client:
            return
        try:
            self.client.set_input_mute(source_name, mute)
        except Exception as e:
            pass

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass


# ─── API SERVER (HTTP + WebSocket) ──────────────────────────────────────────
# Conjunto global de clientes WebSocket conectados
_ws_clients: set = set()
_ws_loop: asyncio.AbstractEventLoop = None


def ws_broadcast(data: dict):
    """Emite un mensaje a todos los clientes WS (thread-safe)."""
    if not _ws_loop or not _ws_clients:
        return
    msg = json.dumps(data)
    async def _send():
        dead = set()
        for ws in list(_ws_clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        _ws_clients.difference_update(dead)
    asyncio.run_coroutine_threadsafe(_send(), _ws_loop)


class APIHandler(BaseHTTPRequestHandler):
    """Handler HTTP embebido que comparte estado con StreamMuter."""
    muter_ref = None  # se asigna antes de iniciar el servidor

    def log_message(self, fmt, *args):
        pass  # silenciar logs HTTP en consola

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def serve_static_file(self, filename, content_type):
        import sys, os
        if getattr(sys, 'frozen', False):
            base_dir = os.path.join(sys._MEIPASS, "web")
        else:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json(404, {"error": "File not found"})

    def do_GET(self):
        m = self.muter_ref
        if self.path == "/" or self.path == "/streammuter.html" or self.path == "/index.html":
            return self.serve_static_file("streammuter.html", "text/html")

        if self.path == "/api/config":
            self._json(200, m.config)

        elif self.path == "/api/status":
            # Detectar qué apps están corriendo en este momento
            running = {}
            for app in m.config.get("apps", []):
                sessions = get_sessions_for_app(app)
                running[app] = len(sessions) > 0

            obs_sources = {}
            if m.obs_ctrl and m.obs_ctrl.client:
                try:
                    inputs = m.obs_ctrl.client.get_input_list().inputs
                    for input_obj in inputs:
                        src = input_obj['inputName']
                        try:
                            # Try to get volume to verify it's an audio source
                            vol = m.obs_ctrl.client.get_input_volume(src).input_volume_mul
                            mute = m.obs_ctrl.client.get_input_mute(src).input_muted
                            obs_sources[src] = {"muted": mute, "volume": vol}
                        except Exception:
                            # Source does not support audio or failed
                            pass
                except Exception:
                    pass

            self._json(200, {
                "muted_obs": m.obs_ctrl.client.get_input_mute(m.config["obs"]["sources_to_mute"][0]).input_muted if m.obs_ctrl and m.config["obs"]["sources_to_mute"] else m.muted_obs,
                "muted_pc":  m.muted_pc,
                "apps":      running,
                "obs_sources": obs_sources,
                "obs_connected": m.obs_ctrl is not None and m.obs_ctrl.client is not None,
            })

        elif self.path == "/api/processes":
            import subprocess
            import csv
            import io
            try:
                output = subprocess.check_output('tasklist /fo csv /nh', shell=True).decode('cp1252', errors='ignore')
                reader = csv.reader(io.StringIO(output))
                exes = set()
                for row in reader:
                    if row and row[0].lower().endswith('.exe'):
                        exes.add(row[0])
                self._json(200, sorted(list(exes), key=str.lower))
            except Exception as e:
                self._json(500, {"error": str(e)})

        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        m = self.muter_ref
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else b"{}"

        if self.path == "/api/config":
            try:
                new_cfg = json.loads(body)
            except json.JSONDecodeError:
                self._json(400, {"error": "JSON inválido"}); return

            # Actualizar config en memoria y en disco
            m.config.update(new_cfg)
            save_config(m.config)

            # Re-registrar hotkeys si cambiaron
            try:
                import keyboard as kb
                kb.unhook_all_hotkeys()
                kb.add_hotkey(m.config.get("hotkey_obs", "f9"),  m.toggle_obs, suppress=False)
                kb.add_hotkey(m.config.get("hotkey_pc",  "f10"), m.toggle_pc,  suppress=False)
                register_mixer_hotkeys(m.config.get("mixer_hotkeys", {}), m)
                print(f"[API] Hotkeys re-registrados: OBS={m.config.get('hotkey_obs')} PC={m.config.get('hotkey_pc')}")
            except Exception as e:
                print(f"[API] Error re-registrando hotkeys: {e}")

            # Reconectar OBS si cambió
            if m.config["obs"]["enabled"]:
                if m.obs_ctrl:
                    m.obs_ctrl.disconnect()
                m.obs_ctrl = OBSController(
                    m.config["obs"]["host"],
                    m.config["obs"]["port"],
                    m.config["obs"]["password"],
                )
                m.obs_ctrl.connect()
            else:
                if m.obs_ctrl:
                    m.obs_ctrl.disconnect()
                m.obs_ctrl = None

            m.draw_console()
            print("[API] Config guardada")
            ws_broadcast({"event": "config_saved"})
            self._json(200, {"ok": True})

        elif self.path == "/api/toggle/obs":
            m.toggle_obs()
            self._json(200, {"muted_obs": m.muted_obs})

        elif self.path == "/api/toggle/pc":
            m.toggle_pc()
            self._json(200, {"muted_pc": m.muted_pc})

        elif self.path == "/api/set_volume":
            try:
                data = json.loads(body)
                app_name = data.get("app")
                new_vol = float(data.get("volume"))
                sessions = get_sessions_for_app(app_name)
                for s in sessions:
                    try:
                        vol = s._ctl.QueryInterface(ISimpleAudioVolume)
                        vol.SetMasterVolume(new_vol, None)
                    except Exception:
                        pass
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})

        elif self.path == "/api/set_mute":
            try:
                data = json.loads(body)
                app_name = data.get("app")
                new_mute = bool(data.get("muted"))
                set_app_mute(app_name, new_mute)
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})

        elif self.path == "/api/obs/set_mute":
            try:
                data = json.loads(body)
                if m.obs_ctrl and m.obs_ctrl.client:
                    m.obs_ctrl.client.set_input_mute(data.get("source"), bool(data.get("muted")))
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})

        elif self.path == "/api/obs/set_volume":
            try:
                data = json.loads(body)
                if m.obs_ctrl and m.obs_ctrl.client:
                    m.obs_ctrl.client.set_input_volume(data.get("source"), vol_mul=float(data.get("volume")))
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})

        else:
            self._json(404, {"error": "Not found"})


async def _ws_handler(websocket):
    """Manejador WebSocket: registra cliente y lo desregistra al desconectar."""
    _ws_clients.add(websocket)
    try:
        # Enviar estado inicial al conectar
        m = APIHandler.muter_ref
        if m:
            await websocket.send(json.dumps({
                "event": "connected",
                "muted_obs": m.muted_obs,
                "muted_pc":  m.muted_pc,
            }))
        # Mantener conexión abierta
        async for _ in websocket:
            pass
    except Exception:
        pass
    finally:
        _ws_clients.discard(websocket)


def start_api_server(muter):
    """Lanza HTTP en hilo separado y WebSocket con asyncio en otro hilo."""
    global _ws_loop

    APIHandler.muter_ref = muter

    # ── HTTP ──
    def run_http():
        httpd = HTTPServer(("0.0.0.0", API_PORT), APIHandler)
        httpd.serve_forever()
    threading.Thread(target=run_http, daemon=True).start()

    # ── WebSocket en puerto API_PORT + 1 (6768) ──
    ws_port = API_PORT + 1

    def run_ws():
        global _ws_loop
        _ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_ws_loop)

        async def telemetry_loop():
            while True:
                if not _ws_clients:
                    await asyncio.sleep(0.5)
                    continue

                m = APIHandler.muter_ref
                if not m:
                    await asyncio.sleep(0.5)
                    continue

                telemetry = {"event": "telemetry", "apps": {}}
                if PYCAW_AVAILABLE:
                    try:
                        all_sessions = AudioUtilities.GetAllSessions()
                        grouped = {}
                        for s in all_sessions:
                            if s.Process:
                                grouped.setdefault(s.Process.name(), []).append(s)
                    except Exception:
                        grouped = {}

                    for app, sessions in grouped.items():
                        
                        max_peak = 0.0
                        vols = []
                        mutes = []
                        for s in sessions:
                            try:
                                meter = s._ctl.QueryInterface(IAudioMeterInformation)
                                vol = s._ctl.QueryInterface(ISimpleAudioVolume)
                                peak = meter.GetPeakValue()
                                if peak > max_peak: max_peak = peak
                                vols.append(vol.GetMasterVolume())
                                mutes.append(vol.GetMute())
                            except Exception:
                                pass
                        
                        if vols:
                            telemetry["apps"][app] = {
                                "peak": max_peak,
                                "volume": sum(vols) / len(vols),
                                "muted": any(mutes)
                            }
                
                ws_broadcast(telemetry)
                await asyncio.sleep(0.06)  # ~16 FPS

        async def main():
            server = websockets.serve(_ws_handler, "0.0.0.0", ws_port)
            await asyncio.gather(server, telemetry_loop())

        _ws_loop.run_until_complete(main())

    threading.Thread(target=run_ws, daemon=True).start()


# ─── MIXER HOTKEYS INDIVIDUALES ────────────────────────────────────────────
def register_mixer_hotkeys(mixer_hotkeys: dict, muter):
    """Registra hotkeys individuales para mutear cada canal del mixer."""
    import keyboard as kb
    for key, combo in mixer_hotkeys.items():
        if not combo:
            continue
        try:
            # key format: "local:Discord.exe" or "obs:Desktop Audio"
            channel_type, channel_name = key.split(':', 1)
        except ValueError:
            continue

        def make_handler(ctype, cname, m, combo_str):
            def handler():
                with m.console_lock:
                    print(f"[Hotkey] Ejecutando {combo_str} → {ctype}:{cname}")
                try:
                    if ctype == 'local':
                        # Para pycaw/COM en hilos nuevos
                        try:
                            import comtypes
                            comtypes.CoInitialize()
                        except: pass
                        
                        sessions = get_sessions_for_app(cname)
                        if sessions:
                            vol = sessions[0]._ctl.QueryInterface(ISimpleAudioVolume)
                            is_muted = vol.GetMute()
                            for s in sessions:
                                try:
                                    s._ctl.QueryInterface(ISimpleAudioVolume).SetMute(not is_muted, None)
                                except: pass
                            m.draw_console()
                            # Notificar
                            m.show_notification(cname, "Silenciado" if not is_muted else "Activado")
                    elif ctype == 'obs':
                        if m.obs_ctrl and m.obs_ctrl.client:
                            # Toggle mute
                            res = m.obs_ctrl.client.get_input_mute(cname)
                            is_muted = res.input_muted
                            m.obs_ctrl.client.set_input_mute(cname, not is_muted)
                            m.draw_console()
                            # Notificar
                            m.show_notification(cname, "Silenciado" if not is_muted else "Activado")
                except Exception as e:
                    print(f"[Hotkey] Error en handler: {e}")
            return handler

        try:
            kb.add_hotkey(combo, make_handler(channel_type, channel_name, muter, combo), suppress=False)
            print(f"[Hotkey] Registrado: {combo} → {key}")
        except Exception as e:
            print(f"[Hotkey] Error registrando '{combo}' para '{key}': {e}")


# ─── LÓGICA PRINCIPAL ───────────────────────────────────────────────────────
class StreamMuter:
    def get_local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def draw_console(self):
        with self.console_lock:
            os.system('cls' if os.name == 'nt' else 'clear')
            hl_obs = "🔇 MUTEADO" if self.muted_obs else "🔊 ACTIVO  "
            hl_pc  = "🔇 MUTEADO" if self.muted_pc else "🔊 ACTIVO  "
            
            local_ip = self.get_local_ip()
            network_url = f"http://{local_ip}:{API_PORT}"
            
            print(f"[LordxMute] ✅ Iniciado - Panel Web: {network_url}")
            print(f"─" * 60)
            print(f" {self.config.get('hotkey_obs', 'f9'):<6} → OBS (Stream) : {hl_obs}")
            print(f" {self.config.get('hotkey_pc',  'f10'):<6} → PC (Local)   : {hl_pc}")
            
            # Mixer Hotkeys
            mixer_keys = self.config.get("mixer_hotkeys", {})
            if mixer_keys:
                print(f"─" * 60)
                for key, combo in mixer_keys.items():
                    if combo:
                        # key format "local:APP.exe" or "obs:SOURCE"
                        try:
                            ktype, kname = key.split(':', 1)
                            display_name = f"{kname} ({ktype})"
                            print(f" {combo:<6} → Mute {display_name[:34]:<34}")
                        except: pass
            
            print(f"─" * 60)
            
            try:
                import qrcode
                import io
                qr = qrcode.QRCode(version=1, box_size=1, border=1)
                qr.add_data(network_url)
                qr.make(fit=True)
                f = io.StringIO()
                qr.print_ascii(out=f)
                qr_lines = f.getvalue().split("\n")
                # Omitting empty lines or lines with garbage
                for line in qr_lines:
                    if "▄" in line or "▀" in line or "█" in line:
                        print("   " + line)
            except Exception:
                pass

            print(f"\nPresiona Ctrl+C para salir.")

    def __init__(self):
        self.config    = load_config()
        self.muted_obs = False
        self.muted_pc  = False
        self.running   = True
        self.obs_ctrl  = None
        self.console_lock = threading.Lock()

        if self.config["obs"]["enabled"]:
            self.obs_ctrl = OBSController(
                self.config["obs"]["host"],
                self.config["obs"]["port"],
                self.config["obs"]["password"],
            )
            self.obs_ctrl.connect()

    def _update_tray(self):
        pass

    def show_notification(self, title, message):
        """Muestra una notificación nativa de Windows 10/11."""
        if self.config.get("notify_on_toggle") and toaster:
            try:
                toaster.show_toast(
                    title,
                    message,
                    duration=3,
                    icon_path=None,
                    threaded=True
                )
            except Exception as e:
                print(f"[Notifier] Error: {e}")

    def toggle_obs(self):
        self.muted_obs = not self.muted_obs
        if self.obs_ctrl and self.config["obs"]["enabled"]:
            for source in self.config["obs"]["sources_to_mute"]:
                self.obs_ctrl.set_source_mute(source, self.muted_obs)
        self._update_tray()
        ws_broadcast({"event": "state", "muted_obs": self.muted_obs, "muted_pc": self.muted_pc})
        self.draw_console()
        
        # Notificar
        state_text = "🔇 MUTEADO" if self.muted_obs else "🔊 ACTIVO"
        self.show_notification("OBS Stream", f"Estado: {state_text}")

    def toggle_pc(self):
        self.muted_pc = not self.muted_pc
        for app in self.config["apps"]:
            set_app_mute(app, self.muted_pc)
        self._update_tray()
        ws_broadcast({"event": "state", "muted_obs": self.muted_obs, "muted_pc": self.muted_pc})
        self.draw_console()
        
        # Notificar
        state_text = "🔇 MUTEADO" if self.muted_pc else "🔊 ACTIVO"
        self.show_notification("PC local", f"Estado: {state_text}")

    def start(self):
        try:
            import keyboard
        except ImportError:
            print("[StreamMuter] ERROR: 'keyboard' no instalado.")
            sys.exit(1)

        hotkey_obs = self.config.get("hotkey_obs", "F9")
        hotkey_pc  = self.config.get("hotkey_pc",  "F10")

        # API HTTP + WebSocket
        start_api_server(self)

        self.draw_console()

        # Hotkeys globales
        keyboard.add_hotkey(hotkey_obs, self.toggle_obs, suppress=False)
        keyboard.add_hotkey(hotkey_pc,  self.toggle_pc,  suppress=False)
        register_mixer_hotkeys(self.config.get("mixer_hotkeys", {}), self)

        # Abrir navegador automáticamente si está habilitado
        if self.config.get("open_browser"):
            import webbrowser
            local_ip = self.get_local_ip()
            webbrowser.open(f"http://{local_ip}:{API_PORT}")

        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\n[StreamMuter] Cerrando...")
        finally:
            if self.obs_ctrl:
                self.obs_ctrl.disconnect()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("StreamMuter solo funciona en Windows.")
        sys.exit(1)

    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        print("[StreamMuter] ⚠️  Sin privilegios de administrador.")
        print("  El hotkey puede no funcionar dentro de juegos.\n")

    muter = StreamMuter()
    muter.start()
