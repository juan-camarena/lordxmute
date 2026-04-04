"""
GUI de configuración para StreamMuter — Dark Premium Edition
"""
import tkinter as tk
from tkinter import messagebox
import json
import os
import ctypes
import sys

CONFIG_FILE = "config.json"

BG_DARK       = "#0f0f13"
BG_CARD       = "#1a1a24"
BG_INPUT      = "#12121a"
ACCENT        = "#7c3aed"
ACCENT_LIGHT  = "#a855f7"
ACCENT_GLOW   = "#4c1d95"
TEXT_PRIMARY  = "#f1f0ff"
TEXT_SECONDARY= "#7c7a99"
TEXT_MUTED    = "#3d3b52"
BORDER        = "#2a2840"
SUCCESS       = "#22c55e"
DANGER        = "#ef4444"
WARNING       = "#f59e0b"

APP_ID = "Lormute.StreamMuter.1"


def set_app_user_model_id():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def make_round_button(parent, text, command, bg=ACCENT, fg=TEXT_PRIMARY,
                      hover_bg=ACCENT_LIGHT, width=120, height=34, font_size=10):
    canvas = tk.Canvas(parent, width=width, height=height,
                       bg=parent["bg"] if hasattr(parent, "winfo_exists") else BG_DARK,
                       highlightthickness=0, cursor="hand2")
    radius = 8

    def draw_btn(color):
        canvas.delete("all")
        canvas.create_arc(0, 0, radius*2, radius*2, start=90, extent=90, fill=color, outline="")
        canvas.create_arc(width-radius*2, 0, width, radius*2, start=0, extent=90, fill=color, outline="")
        canvas.create_arc(0, height-radius*2, radius*2, height, start=180, extent=90, fill=color, outline="")
        canvas.create_arc(width-radius*2, height-radius*2, width, height, start=270, extent=90, fill=color, outline="")
        canvas.create_rectangle(radius, 0, width-radius, height, fill=color, outline="")
        canvas.create_rectangle(0, radius, width, height-radius, fill=color, outline="")
        canvas.create_text(width//2, height//2, text=text, fill=fg,
                           font=("Segoe UI Semibold", font_size))

    draw_btn(bg)
    canvas.bind("<Enter>", lambda e: draw_btn(hover_bg))
    canvas.bind("<Leave>", lambda e: draw_btn(bg))
    canvas.bind("<Button-1>", lambda e: command())
    return canvas


class StyledEntry(tk.Frame):
    def __init__(self, parent, textvariable=None, show=None, width=260, **kw):
        super().__init__(parent, bg=BORDER, padx=1, pady=1)
        self.inner = tk.Frame(self, bg=BG_INPUT)
        self.inner.pack(fill="both", expand=True)
        self.entry = tk.Entry(
            self.inner, textvariable=textvariable, show=show,
            bg=BG_INPUT, fg=TEXT_PRIMARY, insertbackground=ACCENT_LIGHT,
            relief="flat", bd=0, font=("Segoe UI", 10), width=width // 10,
        )
        self.entry.pack(padx=8, pady=6, fill="x")

        def on_focus_in(e): self.config(bg=ACCENT)
        def on_focus_out(e): self.config(bg=BORDER)
        self.entry.bind("<FocusIn>", on_focus_in)
        self.entry.bind("<FocusOut>", on_focus_out)

    def get(self): return self.entry.get()
    def config_entry(self, **kw): self.entry.config(**kw)


class StyledText(tk.Frame):
    def __init__(self, parent, height=4, **kw):
        super().__init__(parent, bg=BORDER, padx=1, pady=1)
        self.inner = tk.Frame(self, bg=BG_INPUT)
        self.inner.pack(fill="both", expand=True)
        self.text = tk.Text(
            self.inner, height=height, bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=ACCENT_LIGHT, relief="flat", bd=0,
            font=("Cascadia Code", 9), selectbackground=ACCENT_GLOW,
            selectforeground=TEXT_PRIMARY, wrap="none",
        )
        self.text.pack(padx=8, pady=6, fill="both", expand=True)

        def on_focus_in(e): self.config(bg=ACCENT)
        def on_focus_out(e): self.config(bg=BORDER)
        self.text.bind("<FocusIn>", on_focus_in)
        self.text.bind("<FocusOut>", on_focus_out)

    def get(self, *args): return self.text.get(*args)
    def insert(self, *args): return self.text.insert(*args)
    def delete(self, *args): return self.text.delete(*args)


class StyledCheckbox(tk.Checkbutton):
    def __init__(self, parent, text, variable, **kw):
        bg = kw.pop("bg", BG_CARD)
        super().__init__(
            parent, text=text, variable=variable,
            bg=bg, fg=TEXT_PRIMARY, activebackground=bg,
            activeforeground=ACCENT_LIGHT, selectcolor=BG_INPUT,
            relief="flat", bd=0, font=("Segoe UI", 10),
            cursor="hand2", highlightthickness=0,
        )


class SectionCard(tk.Frame):
    def __init__(self, parent, title, **kw):
        super().__init__(parent, bg=BG_CARD, padx=0, pady=0,
                         highlightbackground=BORDER, highlightthickness=1)
        header = tk.Frame(self, bg=ACCENT_GLOW, pady=0)
        header.pack(fill="x")
        tk.Label(header, text=f"  {title}", fg=TEXT_PRIMARY, bg=ACCENT_GLOW,
                 font=("Segoe UI Semibold", 10), pady=7).pack(side="left")
        self.content = tk.Frame(self, bg=BG_CARD, padx=16, pady=12)
        self.content.pack(fill="both", expand=True)


class StatusDot(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, width=12, height=12, bg=parent["bg"],
                         highlightthickness=0)
        self._state = "ok"
        self._pulse_alpha = 0
        self._pulse_dir = 1
        self._draw()
        self._animate()

    def _draw(self):
        self.delete("all")
        color = SUCCESS if self._state == "ok" else DANGER
        self.create_oval(1, 1, 11, 11, fill=color, outline="")

    def _animate(self):
        self._pulse_alpha = (self._pulse_alpha + self._pulse_dir * 0.05)
        if self._pulse_alpha >= 1: self._pulse_dir = -1
        elif self._pulse_alpha <= 0: self._pulse_dir = 1
        self._draw()
        self.after(40, self._animate)

    def set_state(self, state):
        self._state = state


# ─── SCROLLBAR ESTILIZADA ───────────────────────────────────────────────────
class StyledScrollbar(tk.Canvas):
    """Scrollbar slim y oscura dibujada en Canvas."""
    def __init__(self, parent, command=None, **kw):
        super().__init__(parent, width=6, bg=BG_DARK,
                         highlightthickness=0, **kw)
        self._command = command
        self._thumb_y0 = 0
        self._thumb_y1 = 0
        self._drag_start = None
        self._drag_thumb_y = None

        self.bind("<ButtonPress-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Configure>", lambda e: self._redraw())

    def set(self, lo, hi):
        self._lo = float(lo)
        self._hi = float(hi)
        self._redraw()

    def _redraw(self):
        self.delete("all")
        h = self.winfo_height()
        if h <= 0:
            return
        lo = getattr(self, "_lo", 0)
        hi = getattr(self, "_hi", 1)

        # Track
        self.create_rectangle(2, 0, 4, h, fill=TEXT_MUTED, outline="", width=0)

        # Thumb
        y0 = int(lo * h)
        y1 = int(hi * h)
        y1 = max(y1, y0 + 20)
        self._thumb_y0 = y0
        self._thumb_y1 = y1

        self.create_rectangle(1, y0, 5, y1, fill=ACCENT, outline="",
                               width=0, tags="thumb")

    def _on_click(self, e):
        if self._thumb_y0 <= e.y <= self._thumb_y1:
            self._drag_start = e.y
            self._drag_lo = getattr(self, "_lo", 0)
        else:
            h = self.winfo_height()
            frac = e.y / h if h else 0
            if self._command:
                self._command("moveto", str(frac))

    def _on_drag(self, e):
        if self._drag_start is None:
            return
        h = self.winfo_height()
        if h <= 0:
            return
        delta = (e.y - self._drag_start) / h
        new_lo = max(0.0, min(1.0, self._drag_lo + delta))
        if self._command:
            self._command("moveto", str(new_lo))


class ConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("StreamMuter")
        self.root.geometry("480x640")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        # Ventana nativa (con barra del sistema normal)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"480x640+{(sw-480)//2}+{(sh-640)//2}")

        # Colorear la barra de título nativa con DWM (Windows 10/11)
        try:
            HWND = ctypes.windll.user32.GetParent(self.root.winfo_id())
            color = 0x00130f0f  # BGR: 0f0f13
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                HWND, 35, ctypes.byref(ctypes.c_int(color)), ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

        set_app_user_model_id()
        self.config = self.load_config()
        self._build_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self._show_toast("Configuracion guardada", SUCCESS)
        except Exception as e:
            self._show_toast(f"Error: {e}", DANGER)

    def _show_toast(self, msg, color=SUCCESS):
        toast = tk.Frame(self.root, bg=color, padx=16, pady=8)
        tk.Label(toast, text=msg, fg="white", bg=color,
                 font=("Segoe UI Semibold", 9)).pack()
        toast.place(relx=0.5, rely=1.0, anchor="s", relwidth=1.0, y=0)
        self.root.after(2200, toast.destroy)

    def _lbl(self, parent, text, secondary=False, size=9):
        color = TEXT_SECONDARY if secondary else TEXT_PRIMARY
        return tk.Label(parent, text=text, fg=color, bg=parent["bg"],
                        font=("Segoe UI", size))

    def _build_ui(self):
        # Barra de acento superior (debajo de la barra nativa)
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill="x")

        # Header
        header = tk.Frame(self.root, bg=BG_DARK, pady=0)
        header.pack(fill="x")

        logo_frame = tk.Frame(header, bg=BG_DARK, pady=18, padx=22)
        logo_frame.pack(fill="x")

        title_frame = tk.Frame(logo_frame, bg=BG_DARK)
        title_frame.pack(side="left")
        tk.Label(title_frame, text="StreamMuter", fg=TEXT_PRIMARY, bg=BG_DARK,
                 font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(title_frame, text="Configuracion de hotkeys y apps",
                 fg=TEXT_SECONDARY, bg=BG_DARK,
                 font=("Segoe UI", 9)).pack(anchor="w")

        self.status_dot = StatusDot(logo_frame)
        self.status_dot.pack(side="right", padx=(0, 4))
        tk.Label(logo_frame, text="Activo", fg=SUCCESS, bg=BG_DARK,
                 font=("Segoe UI", 9)).pack(side="right")

        # Scroll area
        outer = tk.Frame(self.root, bg=BG_DARK)
        outer.pack(fill="both", expand=True, padx=14, pady=0)

        canvas = tk.Canvas(outer, bg=BG_DARK, highlightthickness=0)
        scrollbar = StyledScrollbar(outer, command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=BG_DARK)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y", padx=(2, 0))
        canvas.pack(side="left", fill="both", expand=True)

        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._build_sections(self.scroll_frame)

        # Footer
        footer = tk.Frame(self.root, bg=BG_DARK, pady=12)
        footer.pack(fill="x", side="bottom")

        make_round_button(footer, "Guardar", self.save_changes,
                          width=130, height=36, font_size=10
                          ).pack(side="right", padx=(6, 16))

        make_round_button(footer, "Cancelar", self.root.quit,
                          bg="#2a2840", hover_bg="#3d3b52",
                          width=120, height=36, font_size=10
                          ).pack(side="right", padx=4)

    def _build_sections(self, parent):
        pad = {"fill": "x", "pady": 7}

        # HOTKEYS
        s1 = SectionCard(parent, "HOTKEYS")
        s1.pack(**pad)
        c1 = s1.content

        self._lbl(c1, "Hotkey OBS  (mutea solo el stream)").grid(row=0, column=0, sticky="w", pady=(0,2))
        self.hotkey_obs_var = tk.StringVar(value=self.config.get("hotkey_obs", "F9"))
        StyledEntry(c1, textvariable=self.hotkey_obs_var, width=160).grid(row=1, column=0, sticky="w", pady=(0,10))

        self._lbl(c1, "Hotkey PC  (mutea tu audio local)").grid(row=2, column=0, sticky="w", pady=(0,2))
        self.hotkey_pc_var = tk.StringVar(value=self.config.get("hotkey_pc", "F10"))
        StyledEntry(c1, textvariable=self.hotkey_pc_var, width=160).grid(row=3, column=0, sticky="w")

        # APLICACIONES
        s2 = SectionCard(parent, "APLICACIONES")
        s2.pack(**pad)
        c2 = s2.content

        self._lbl(c2, "Procesos a mutear  (uno por linea)").pack(anchor="w", pady=(0,4))
        self._lbl(c2, "ej: Spotify.exe, VALORANT-Win64-Shipping.exe",
                  secondary=True, size=8).pack(anchor="w", pady=(0,6))
        self.apps_text = StyledText(c2, height=4)
        self.apps_text.pack(fill="x")
        self.apps_text.insert("1.0", "\n".join(self.config.get("apps", [])))

        # OBS
        s3 = SectionCard(parent, "OBS WEBSOCKET")
        s3.pack(**pad)
        c3 = s3.content

        self.obs_enabled_var = tk.BooleanVar(value=self.config.get("obs", {}).get("enabled", False))
        StyledCheckbox(c3, "Habilitar integracion OBS", self.obs_enabled_var,
                       bg=BG_CARD).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))

        fields = [
            ("Host:", "obs_host_var", self.config.get("obs", {}).get("host", "localhost"), None),
            ("Puerto:", "obs_port_var", str(self.config.get("obs", {}).get("port", 4455)), None),
            ("Contrasena:", "obs_password_var", self.config.get("obs", {}).get("password", ""), "*"),
        ]
        for i, (label, attr, val, show) in enumerate(fields, start=1):
            self._lbl(c3, label).grid(row=i*2-1, column=0, sticky="w", pady=(0,2))
            var = tk.StringVar(value=val)
            setattr(self, attr, var)
            entry = StyledEntry(c3, textvariable=var, show=show, width=280)
            entry.grid(row=i*2, column=0, sticky="w", pady=(0,8))
            if show:
                self._password_entry = entry

        self.show_pw_var = tk.BooleanVar(value=False)
        def toggle_pw():
            self._password_entry.config_entry(show="" if self.show_pw_var.get() else "*")
        StyledCheckbox(c3, "Mostrar contrasena", self.show_pw_var,
                       bg=BG_CARD).grid(row=8, column=0, sticky="w", pady=(0,10))
        self.show_pw_var.trace_add("write", lambda *_: toggle_pw())

        self._lbl(c3, "Fuentes OBS a mutear  (una por linea):").grid(row=9, column=0, sticky="w", pady=(0,2))
        self._lbl(c3, "ej: SPOTIFY, VALORANT", secondary=True, size=8).grid(row=10, column=0, sticky="w", pady=(0,6))
        self.obs_sources_text = StyledText(c3, height=3)
        self.obs_sources_text.grid(row=11, column=0, sticky="ew", pady=(0,4))
        self.obs_sources_text.insert("1.0", "\n".join(self.config.get("obs", {}).get("sources_to_mute", [])))

        # OPCIONES
        s4 = SectionCard(parent, "OTRAS OPCIONES")
        s4.pack(fill="x", pady=(7, 2))
        c4 = s4.content

        self.show_tray_var = tk.BooleanVar(value=self.config.get("show_tray", True))
        StyledCheckbox(c4, "Mostrar icono en bandeja del sistema",
                       self.show_tray_var, bg=BG_CARD).pack(anchor="w")

        tk.Frame(parent, bg=BG_DARK, height=12).pack()

    def save_changes(self):
        self.config["hotkey_obs"] = self.hotkey_obs_var.get()
        self.config["hotkey_pc"]  = self.hotkey_pc_var.get()

        apps_text = self.apps_text.get("1.0", tk.END).strip()
        self.config["apps"] = [ln.strip() for ln in apps_text.split("\n") if ln.strip()]

        if "obs" not in self.config:
            self.config["obs"] = {}

        self.config["obs"]["enabled"] = self.obs_enabled_var.get()
        self.config["obs"]["host"]    = self.obs_host_var.get()
        try:
            self.config["obs"]["port"] = int(self.obs_port_var.get())
        except ValueError:
            self._show_toast("El puerto debe ser un numero", DANGER)
            return

        self.config["obs"]["password"] = self.obs_password_var.get()

        sources_text = self.obs_sources_text.get("1.0", tk.END).strip()
        self.config["obs"]["sources_to_mute"] = [
            ln.strip() for ln in sources_text.split("\n") if ln.strip()
        ]

        self.config["show_tray"] = self.show_tray_var.get()
        self.save_config()


def main():
    set_app_user_model_id()
    root = tk.Tk()
    app = ConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()