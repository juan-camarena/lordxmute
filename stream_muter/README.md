# 🔇 StreamMuter

Hotkey para mutear/desmutear Spotify y tu juego **solo para el stream**, sin afectar el audio de tu PC. Integración opcional con OBS.

---

## ⚡ Instalación rápida

1. Instala [Python 3.10+](https://python.org) — marca ✅ "Add to PATH"
2. Haz doble clic en **`INSTALAR.bat`**
3. Edita **`config.json`** con tu configuración
4. Ejecuta **`START.bat`** (pedirá admin automáticamente)

---

## ⚙️ Configuración (`config.json`)

```json
{
  "hotkey": "F9",
  "apps": [
    "Spotify.exe",
    "r5apex.exe"
  ],
  "obs": {
    "enabled": false,
    "host": "localhost",
    "port": 4455,
    "password": "tu_password_obs",
    "sources_to_mute": ["Spotify", "Juego"]
  },
  "show_tray": true,
  "notify_on_toggle": true
}
```

### Parámetros

| Campo | Descripción |
|-------|-------------|
| `hotkey` | Tecla para alternar mute. Ej: `F9`, `ctrl+m`, `F8` |
| `apps` | Lista de procesos `.exe` a mutear |
| `obs.enabled` | `true` para activar integración OBS |
| `obs.password` | En OBS → Herramientas → WebSocket Server Settings |
| `obs.sources_to_mute` | Nombres exactos de las fuentes de audio en tu escena de OBS |
| `show_tray` | Ícono verde/rojo en la bandeja del sistema |
| `notify_on_toggle` | Notificación de Windows al hacer toggle |

---

## 🎮 Ejemplos de nombres `.exe` de juegos comunes

| Juego | Ejecutable |
|-------|-----------|
| Apex Legends | `r5apex.exe` |
| Valorant | `VALORANT-Win64-Shipping.exe` |
| CS2 | `cs2.exe` |
| Fortnite | `FortniteClient-Win64-Shipping.exe` |
| League of Legends | `League of Legends.exe` |
| Minecraft (Java) | `javaw.exe` |
| Warzone | `cod.exe` |

> **¿Cómo saber el .exe de tu juego?**
> Abre el Task Manager (Ctrl+Shift+Esc) → pestaña "Detalles" → busca tu juego corriendo.

---

## 📡 Integración OBS

1. En OBS: **Herramientas → WebSocket Server Settings**
2. Activa "Enable WebSocket server"
3. Anota el puerto y crea un password
4. En `config.json`, pon `"enabled": true` y llena `host`, `port`, `password`
5. En `sources_to_mute`, pon los **nombres exactos** de tus fuentes de audio en OBS

Con esto, el hotkey también muteará directamente las fuentes en tu software de stream.

---

## 💡 Tips

- **¿El hotkey no funciona en juegos?** Ejecuta `START.bat` como Administrador (ya lo hace automático).
- **¿Spotify no se mutea?** Asegúrate que Spotify esté reproduciendo algo cuando presiones el hotkey.
- **Múltiples hotkeys**: Puedes correr varias instancias con distintos `config.json` si necesitas controlar cosas por separado.
- El mute es **por sesión de audio**, no del sistema — el resto de tu PC sigue escuchando normal.

---

## 🧩 Dependencias

- `pycaw` — Control de audio por app (Windows Core Audio)
- `keyboard` — Hotkeys globales
- `pystray` + `Pillow` — Ícono en bandeja
- `obsws-python` — OBS WebSocket (opcional)
- `win10toast` — Notificaciones Windows (opcional)
