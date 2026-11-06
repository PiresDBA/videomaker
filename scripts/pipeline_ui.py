# -*- coding: utf-8 -*-
"""
Videomaker - Interface Premium do Pipeline v3 (tkinter).

Interface super premium, construída para competir com as melhores UIs de
produção de vídeo do mundo. Recursos:

  - Barra lateral: Criar / Publicar / Diário / Atividade / Ajustes
  - Zoom de interface: A+ / A- / reset, com atalhos (Ctrl+=, Ctrl+-, Ctrl+0)
  - Daily Runner integrado: fila de tópicos, execução automática, status
  - Etapas como "chips" com progresso ao vivo (checkpoints)
  - Barra de ação fixa: status, progresso e botões principais
  - YouTube: envio manual, automático ou com confirmação
  - Tema claro/escuro automático, DPI nítido no Windows
  - Configurações persistidas em pipeline_ui_settings.json
  - Atalhos: Ctrl+Enter gerar, Ctrl+= zoom in, Ctrl+- zoom out, Ctrl+0 reset

Uso:
  python scripts/pipeline_ui.py [-p "<prompt>"] [--theme auto|light|dark]
"""
import argparse
import ast
import calendar
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
import unicodedata
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PIPELINE = HERE / "pipeline.py"
UPLOADER = HERE / "youtube_upload.py"
DAILY = HERE / "daily_runner.py"
TOPICS = HERE / "topics.txt"
SETTINGS = HERE / "pipeline_ui_settings.json"

# -------------------------------------------------------------- tema premium ---
# Paleta premium: índigo profundo, acento violeta, semânticos refinados
LIGHT = {
    "bg": "#F8F9FC", "sidebar": "#FFFFFF", "card": "#FFFFFF", "field": "#F2F4F8",
    "border": "#E5E7EB", "border2": "#D1D5DB", "text": "#0F172A", "text2": "#475569",
    "text3": "#94A3B8", "accent": "#6366F1", "accent_h": "#4F46E5", "accent_p": "#4338CA",
    "on_accent": "#FFFFFF", "fill": "#F1F5F9", "fill_h": "#E2E8F0", "fill_p": "#CBD5E1",
    "chip_on": "#EFF6FF", "nav_sel": "#F1F5F9",
    "ok": "#10B981", "err": "#EF4444", "warn": "#F59E0B",
    "seg_track": "#F1F5F9", "seg_thumb": "#FFFFFF",
    "toast": "#0F172A", "on_toast": "#FFFFFF", "shadow": "#CBD5E1",
    "log_bg": "#020617", "log_fg": "#CBD5E1",
}
DARK = {
    "bg": "#0B0F19", "sidebar": "#0F172A", "card": "#111827", "field": "#1E293B",
    "border": "#1E293B", "border2": "#334155", "text": "#F8FAFC", "text2": "#94A3B8",
    "text3": "#64748B", "accent": "#818CF8", "accent_h": "#A5B4FC", "accent_p": "#6366F1",
    "on_accent": "#FFFFFF", "fill": "#1E293B", "fill_h": "#334155", "fill_p": "#475569",
    "chip_on": "#1E1B4B", "nav_sel": "#1E293B",
    "ok": "#34D399", "err": "#F87171", "warn": "#FBBF24",
    "seg_track": "#1E293B", "seg_thumb": "#374151",
    "toast": "#F8FAFC", "on_toast": "#0F172A", "shadow": "#000000",
    "log_bg": "#020617", "log_fg": "#CBD5E1",
}

ZOOM_LEVELS = [0.75, 1.0, 1.25, 1.5]
ZOOM_IDX_DEFAULT = 1

T = dict(LIGHT)
SCALE = 1.0
ZOOM_IDX = ZOOM_IDX_DEFAULT
FAMILY, MONO = "Segoe UI Variable Text", "Segoe UI Variable Mono"
PULSE = [False]

# chave, titulo curto, descricao
PHASES = [
    ("script", "Roteiro", "IA web · Gemini"),
    ("scenes", "Cenas", "IA · HTML"),
    ("images", "Imagens", "IA web · Gemini"),
    ("music", "Música", "IA web / procedural"),
    ("narration", "Narração", "Gemini (AI Studio) / Edge-TTS"),
    ("timeline", "Timeline", "Linha do tempo"),
    ("mix", "Mixagem", "Áudio final"),
    ("compose", "Composição", "HyperFrames"),
    ("preprocess", "Pré-process.", "Imagens"),
    ("render", "Render", "MP4 final"),
]
PHASE_KEYS = [k for k, _, _ in PHASES]
PHASE_NAME = {k: n for k, n, _ in PHASES}

RUN_MODES = [("auto", "Automático"), ("from", "A partir de"), ("only", "Somente"), ("skip", "Pular")]
YT_MODES = [("manual", "Manual"), ("auto", "Automático"), ("ask", "Perguntar")]
YT_PRIVACY = [("private", "Privado"), ("unlisted", "Não listado"), ("public", "Público")]
YT_MODE_HELP = {
    "manual": "Nada é enviado sozinho. Use o botão Enviar quando quiser.",
    "auto": "Assim que o render terminar, o vídeo é enviado automaticamente.",
    "ask": "Ao terminar o render, perguntamos se você quer enviar agora.",
}
PRIV_HELP = {
    "private": "Só você vê. Ideal para revisar no YouTube Studio antes de publicar.",
    "unlisted": "Qualquer pessoa com o link pode assistir.",
    "public": "Aparece no canal e nas buscas assim que o envio terminar.",
}
PLACEHOLDER = "Ex.: A história do buldogue inglês, em pixel art estilo animação 3D"
PAGE_TEXT = {
    "create": ("Criar", "Descreva o vídeo e escolha quais etapas executar."),
    "publish": ("Publicar", "Envie o MP4 final para o seu canal do YouTube."),
    "daily": ("Diário", "Execução automática diária a partir da fila de tópicos."),
    "activity": ("Atividade", "Acompanhe a execução em tempo real."),
    "executivo": ("Executivo", "Painel gerencial com KPIs, gauges e telemetria"),
    "settings": ("Ajustes", "Tema, zoom e preferências da interface"),
}



def P(n):
    return int(round(n * SCALE))


def fnt(size, bold=False, mono=False):
    """Fonte com zoom aplicado."""
    global ZOOM_IDX
    eff = size * ZOOM_LEVELS[ZOOM_IDX]
    return (MONO if mono else FAMILY, max(6, int(round(eff))), "bold" if bold else "normal")


def init_fonts(root):
    global FAMILY, MONO
    fams = set(tkfont.families(root))
    for f in ("SF Pro Text", "Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", "Inter", "Cantarell",
              "DejaVu Sans", "Arial"):
        if f in fams:
            FAMILY = f
            break
    for f in ("SF Mono", "Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"):
        if f in fams:
            MONO = f
            break


def detect_dark():
    try:
        if sys.platform == "win32":
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
        if sys.platform == "darwin":
            r = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                               capture_output=True, text=True)
            return "Dark" in r.stdout
    except Exception:
        pass
    return False


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rr(cv, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
           x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, x1 + r, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def fit_text(text, font, maxw):
    f = tkfont.Font(font=font)
    if f.measure(text) <= maxw:
        return text
    while len(text) > 1 and f.measure(text + "…") > maxw:
        text = text[:-1]
    return text + "…"


def slugify(text, max_len=40):
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    norm = re.sub(r"[^a-z0-9\s-]", "", norm.lower())
    norm = re.sub(r"[\s_-]+", "-", norm).strip("-")
    return norm[:max_len].rstrip("-")


def fmt_dur(s):
    m, r = divmod(int(s), 60)
    if m == 0:
        return "%d s" % r
    return "%d min %02d s" % (m, r) if r else "%d min" % m


def load_state(slug):
    try:
        return json.loads((ROOT / "projects" / slug / "project.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def done_phases(slug):
    if not slug:
        return set()
    ph = load_state(slug).get("phases") or {}
    return {k for k, v in ph.items() if isinstance(v, dict) and v.get("done")}


def list_projects():
    out, d = [], ROOT / "projects"
    if not d.is_dir():
        return out
    for p in d.iterdir():
        sf = p / "project.json"
        if not sf.is_file():
            continue
        try:
            st = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            st = {}
        done = sum(1 for v in (st.get("phases") or {}).values() if isinstance(v, dict) and v.get("done"))
        out.append({"slug": p.name, "prompt": st.get("prompt") or "", "done": done,
                    "video": (p / "output" / ("%s.mp4" % p.name)).is_file(), "mtime": sf.stat().st_mtime})
    out.sort(key=lambda x: -x["mtime"])
    return out


def open_path(path):
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


def _sh(cmd):
    return " ".join('"%s"' % c if (not c or (not c[0].isalnum() and c[0] != "-")) else c for c in cmd)


def lbl(parent, text="", size=10, bold=False, color="text", bg=None, **kw):
    return tk.Label(parent, text=text, font=fnt(size, bold), fg=T[color], bg=bg or T["card"], **kw)


# ---------------------------------------------------------------- widgets ---
class Card(tk.Canvas):
    """Superfície arredondada com sombra sutil. Conteúdo em card.body."""

    def __init__(self, master, pad=20, radius=14, fill=None, outline=None, autoheight=True, bg=None,
                 elevated=False):
        self._h = P(60) if autoheight else P(200)
        super().__init__(master, bg=bg or T["bg"], highlightthickness=0, bd=0, height=self._h, width=P(10))
        self._pad, self._r, self._auto = P(pad), P(radius), autoheight
        self._fill, self._out = fill or T["card"], outline or T["border"]
        self._elevated = elevated
        self.body = tk.Frame(self, bg=self._fill)
        self._win = self.create_window(self._pad, self._pad, window=self.body, anchor="nw")
        self.bind("<Configure>", self._redraw)
        if autoheight:
            self.body.bind("<Configure>", self._fit)

    def _fit(self, e=None):
        h = self.body.winfo_reqheight() + 2 * self._pad
        if abs(h - self._h) > 1:
            self._h = h
            self.configure(height=h)

    def _redraw(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        self.delete("bg")
        if self._elevated:
            rr(self, 3, 3, w + 1, h + 1, self._r, fill=T["shadow"], outline="")
        rr(self, 1, 1, w - 1, h - 1, self._r, fill=self._fill, outline=self._out, tags="bg")
        self.tag_lower("bg")
        kw = {"width": max(10, w - 2 * self._pad)}
        if not self._auto:
            kw["height"] = max(10, h - 2 * self._pad)
        self.itemconfigure(self._win, **kw)


class Button(tk.Canvas):
    def __init__(self, master, text, command=None, kind="secondary", h=34, padx=18, size=10, bg=None,
                 icon=""):
        self.txt, self.cmd, self.kind, self.icon = text, command, kind, icon
        self.enabled, self.hov, self.down = True, False, False
        self._font = fnt(size, True)
        self._bgc = bg or T["card"]
        label = (icon + " " if icon else "") + text
        w = tkfont.Font(font=self._font).measure(label) + 2 * P(padx)
        super().__init__(master, width=w, height=P(h), bg=self._bgc, highlightthickness=0, bd=0,
                         cursor="hand2")
        self.bind("<Enter>", lambda e: self._set(hov=True))
        self.bind("<Leave>", lambda e: self._set(hov=False, down=False))
        self.bind("<ButtonPress-1>", lambda e: self._set(down=True))
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self._draw()

    def _release(self, e):
        was = self.down
        self._set(down=False)
        if was and self.enabled and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height() and self.cmd:
            self.cmd()

    def set_enabled(self, on):
        self.enabled = on
        self.configure(cursor="hand2" if on else "arrow")
        self._draw()

    def set_text(self, text):
        self.txt = text
        self._draw()

    def _colors(self):
        k = self.kind
        if not self.enabled:
            return T["fill"], T["text3"]
        if k == "primary":
            return (T["accent_p"] if self.down else T["accent_h"] if self.hov else T["accent"]), T["on_accent"]
        if k == "ghost":
            return (T["fill_h"] if self.hov else self._bgc), T["accent"]
        if k == "danger":
            return (T["fill_p"] if self.down else T["fill_h"] if self.hov else T["fill"]), T["err"]
        return (T["fill_p"] if self.down else T["fill_h"] if self.hov else T["fill"]), T["text"]

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        fill, fg = self._colors()
        rr(self, 0, 0, w, h, h / 2, fill=fill, outline=fill)
        label = (self.icon + " " if self.icon else "") + self.txt
        self.create_text(w / 2, h / 2, text=label, font=self._font, fill=fg)


class Switch(tk.Canvas):
    def __init__(self, master, var, bg=None):
        self.var = var
        self.pos = 1.0 if var.get() else 0.0
        super().__init__(master, width=P(44), height=P(26), bg=bg or T["card"], highlightthickness=0, bd=0,
                         cursor="hand2")
        self.bind("<Button-1>", lambda e: self.var.set(not var.get()))
        var.trace_add("write", lambda *a: self._anim())
        self._draw()

    def _anim(self):
        target = 1.0 if self.var.get() else 0.0
        if abs(self.pos - target) < 0.01:
            self.pos = target
        else:
            self.pos += 0.34 if target > self.pos else -0.34
            self.pos = max(0.0, min(1.0, self.pos))
            self.after(14, self._anim)
        self._draw()

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w, h = P(44), P(26)
        rr(self, 0, 0, w, h, h / 2, fill=mix(T["fill_p"], T["accent"], self.pos), outline="")
        r, pad = h / 2 - P(3), P(3)
        cx = pad + r + (w - 2 * pad - 2 * r) * self.pos
        self.create_oval(cx - r, h / 2 - r + 1, cx + r, h / 2 + r + 1, fill=T["shadow"], outline="")
        self.create_oval(cx - r, h / 2 - r, cx + r, h / 2 + r, fill="#FFFFFF", outline="")


class Segmented(tk.Canvas):
    def __init__(self, master, opts, var, h=32, bg=None):
        self.opts, self.var = opts, var
        tf = tkfont.Font(font=fnt(9, True))
        self.seg_w = max(tf.measure(l) for _, l in opts) + P(30)
        super().__init__(master, width=self.seg_w * len(opts) + P(6), height=P(h), bg=bg or T["card"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", self._click)
        var.trace_add("write", lambda *a: self._draw())
        self._draw()

    def _click(self, e):
        i = max(0, min(len(self.opts) - 1, int((e.x - P(3)) // self.seg_w)))
        self.var.set(self.opts[i][0])

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        rr(self, 0, 0, w, h, P(10), fill=T["seg_track"], outline=T["border"])
        for i, (k, label) in enumerate(self.opts):
            x1 = P(3) + i * self.seg_w
            sel = self.var.get() == k
            if sel:
                rr(self, x1, P(3), x1 + self.seg_w, h - P(3), P(8), fill=T["seg_thumb"], outline=T["border"])
            self.create_text(x1 + self.seg_w / 2, h / 2, text=label, font=fnt(9, sel),
                             fill=T["text"] if sel else T["text2"])


class Slider(tk.Canvas):
    def __init__(self, master, var, lo, hi, step=10, bg=None):
        self.var, self.lo, self.hi, self.step = var, lo, hi, step
        super().__init__(master, height=P(28), width=P(10), bg=bg or T["card"], highlightthickness=0, bd=0,
                         cursor="hand2")
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._set)
        self.bind("<B1-Motion>", self._set)
        var.trace_add("write", lambda *a: self._draw())

    def _set(self, e):
        pad, w = P(12), max(1, self.winfo_width())
        t = max(0.0, min(1.0, (e.x - pad) / max(1, w - 2 * pad)))
        v = self.lo + t * (self.hi - self.lo)
        self.var.set(int(max(self.lo, min(self.hi, round(v / self.step) * self.step))))

    def _draw(self):
        if not self.winfo_exists():
            return
        w, h = self.winfo_width(), self.winfo_height()
        if w < 30:
            return
        self.delete("all")
        pad, cy = P(12), h / 2
        t = (self.var.get() - self.lo) / float(self.hi - self.lo)
        x = pad + (w - 2 * pad) * max(0.0, min(1.0, t))
        rr(self, pad, cy - P(3), w - pad, cy + P(3), P(3), fill=T["fill_h"], outline="")
        rr(self, pad, cy - P(3), x, cy + P(3), P(3), fill=T["accent"], outline="")
        r = P(10)
        self.create_oval(x - r, cy - r + 1, x + r, cy + r + 1, fill=T["shadow"], outline="")
        self.create_oval(x - r, cy - r, x + r, cy + r, fill="#FFFFFF", outline=T["border2"])


class ProgressBar(tk.Canvas):
    def __init__(self, master, bg=None):
        super().__init__(master, height=P(6), width=P(10), bg=bg or T["bg"], highlightthickness=0, bd=0)
        self.value, self.indet, self._job = 0.0, False, None
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, v):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        if v is None:
            self.indet = True
            self._anim()
        else:
            self.indet = False
            self.value = max(0.0, min(1.0, v))
            self._draw()

    def _anim(self):
        if not self.indet:
            return
        self._draw()
        self._job = self.after(30, self._anim)

    def _draw(self):
        if not self.winfo_exists():
            return
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            return
        self.delete("all")
        rr(self, 0, 0, w, h, h / 2, fill=T["fill_h"], outline="")
        if self.indet:
            t = (time.time() * 0.9) % 1.4 - 0.2
            x1, x2 = max(0, t * w), min(w, t * w + 0.3 * w)
        else:
            x1, x2 = 0, w * self.value
            if self.value > 0:
                x2 = max(x2, h)
        if x2 - x1 > 1:
            rr(self, x1, 0, x2, h, h / 2, fill=T["accent"], outline="")


class StatusPill(tk.Canvas):
    def __init__(self, master, bg=None):
        super().__init__(master, height=P(30), bg=bg or T["bg"], highlightthickness=0, bd=0)
        self.kind, self.text = "idle", "Pronto"
        self.set("idle", "Pronto")

    def set(self, kind, text):
        self.kind, self.text = kind, text
        w = tkfont.Font(font=fnt(9, True)).measure(text) + P(40)
        self.configure(width=w)
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        rr(self, 0, 0, w, h, h / 2, fill=T["card"], outline=T["border"])
        col = {"idle": T["text3"], "ok": T["ok"], "err": T["err"],
               "run": T["accent"] if PULSE[0] else mix(T["accent"], T["card"], 0.55)}[self.kind]
        self.create_oval(P(13), h / 2 - P(4), P(21), h / 2 + P(4), fill=col, outline="")
        self.create_text(P(30), h / 2, text=self.text, anchor="w", font=fnt(9, True), fill=T["text"])


# ----------------------------------------------------------- calendario ---

class CalendarDay(tk.Canvas):
    """Um dia individual no calendario premium."""
    def __init__(self, master, date, events, on_click, today=False, selected=False, bg=None):
        super().__init__(master, width=P(42), height=P(56), bg=bg or T["card"], highlightthickness=0, bd=0,
                         cursor="hand2")
        self.date = date
        self.events = events
        self.on_click = on_click
        self.today = today
        self.selected = selected
        self.hov = False
        self.bind("<Enter>", lambda e: self._set(hov=True))
        self.bind("<Leave>", lambda e: self._set(hov=False))
        self.bind("<Button-1>", lambda e: self.on_click(self))
        self._draw()

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self._draw()

    def set_selected(self, on):
        self.selected = on
        self._draw()

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        d = self.date
        is_today = self.today
        is_sel = self.selected

        # fundo
        if is_sel:
            rr(self, 0, 0, w, h, P(10), fill=T["accent"], outline="")
            txt_col = "#FFFFFF"
            num_col = "#FFFFFF"
        elif is_today:
            rr(self, 0, 0, w, h, P(10), fill=T["fill_h"], outline=T["accent"])
            txt_col = T["text"]
            num_col = T["accent"]
        elif self.hov:
            rr(self, 0, 0, w, h, P(10), fill=T["fill"], outline="")
            txt_col = T["text"]
            num_col = T["text"]
        else:
            rr(self, 0, 0, w, h, P(10), fill=T["card"], outline="")
            txt_col = T["text"]
            num_col = T["text2"]

        # numero do dia
        self.create_text(P(21), P(16), text=str(d.day), font=fnt(12, True), fill=num_col, anchor="center")

        # dots de eventos
        if self.events:
            ndots = min(len(self.events), 4)
            dot_w = P(5)
            total = ndots * dot_w + (ndots - 1) * P(2)
            x0 = (w - total) / 2
            y0 = P(36)
            for i in range(ndots):
                col = T["ok"] if i % 2 == 0 else T["accent"]
                cx = x0 + i * (dot_w + P(2)) + dot_w / 2
                self.create_oval(cx - dot_w / 2, y0 - dot_w / 2, cx + dot_w / 2, y0 + dot_w / 2,
                                 fill=col, outline="")


class CalendarHeader(tk.Frame):
    """Cabecalho com mes/ano e botoes de navegacao."""
    def __init__(self, master, on_prev, on_next, on_today, label):
        super().__init__(master, bg=T["card"])
        self.on_prev = on_prev
        self.on_next = on_next
        self.on_today = on_today
        self.label = lbl(self, label, 11, True).pack(side="left", padx=(P(12), 0), pady=P(10))
        btns = tk.Frame(self, bg=T["card"])
        btns.pack(side="right", padx=(0, P(12)), pady=P(10))
        Button(btns, "<", on_prev, "ghost", h=26, padx=6, size=9).pack(side="left", padx=(0, P(4)))
        Button(btns, "Hoje", on_today, "secondary", h=26, padx=10, size=8).pack(side="left", padx=(0, P(4)))
        Button(btns, ">", on_next, "ghost", h=26, padx=6, size=9).pack(side="left")


class CalendarMonth(tk.Frame):
    """Visual mensal em grade 7x6 com eventos por dia."""
    def __init__(self, master, events_by_date, on_day_click, today=None):
        super().__init__(master, bg=T["card"])
        self.events_by_date = events_by_date
        self.on_day_click = on_day_click
        self.today = today or datetime.now()
        self.year = self.today.year
        self.month = self.today.month
        self.selected = None
        self.day_widgets = {}
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        # cabecalho dias da semana
        dow_frame = tk.Frame(self, bg=T["card"])
        dow_frame.pack(fill="x", padx=P(8), pady=(P(10), P(4)))
        dow_names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
        for i, name in enumerate(dow_names):
            lbl(dow_frame, name, 9, True, "text3").grid(row=0, column=i, padx=0, pady=0)
            dow_frame.grid_columnconfigure(i, weight=1, uniform="cal")

        # grade de dias
        self.grid_frame = tk.Frame(self, bg=T["card"])
        self.grid_frame.pack(fill="both", expand=True, padx=P(8), pady=(0, P(10)))

        cal = calendar.Calendar(firstweekday=0)
        month_days = list(cal.itermonthdates(self.year, self.month))

        row = 0
        col = 0
        for d in month_days:
            is_current = d.month == self.month
            is_today = d == self.today.date()
            is_sel = (self.selected is not None and d == self.selected.date)
            events = self.events_by_date.get(d.isoformat(), [])

            day = CalendarDay(self.grid_frame, d, events, self._on_day_selected,
                              today=is_today, selected=is_sel)
            day.grid(row=row, column=col, padx=P(2), pady=P(2), sticky="nsew")
            self.day_widgets[d.isoformat()] = day
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="cal")

            col += 1
            if col > 6:
                col = 0
                row += 1
                self.grid_frame.grid_rowconfigure(row, weight=1, uniform="cal")

    def _on_day_selected(self, day_widget):
        self.selected = day_widget
        self._build()
        if self.on_day_click:
            self.on_day_click(day_widget.date)

    def set_month(self, year, month):
        self.year = year
        self.month = month
        self._build()

    def prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self._build()

    def next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self._build()

    def go_today(self):
        self.today = datetime.now()
        self.year = self.today.year
        self.month = self.today.month
        self.selected = None
        self._build()


# ------------------------------------------------------ agendamento utils ---

SCHEDULE_FILE = ROOT / "scheduled_videos.json"
API_HEALTH = "http://127.0.0.1:8765/api/health"


def load_schedules():
    try:
        return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"scheduled_videos": []}


def save_schedules(data):
    try:
        SCHEDULE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def events_for_date(schedules, date_str):
    return [s for s in schedules.get("scheduled_videos", []) if s.get("date") == date_str]


def schedules_for_range(schedules, start_date, end_date):
    out = []
    for s in schedules.get("scheduled_videos", []):
        try:
            d = datetime.strptime(s["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if start_date <= d <= end_date:
            out.append(s)
    return out


def add_schedule(date_str, time_str, prompt, recurrence="none", weekdays=None):
    data = load_schedules()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "date": date_str,
        "time": time_str,
        "prompt": prompt,
        "source": "topic" if (prompt or "").strip() else "queue",
        "recurrence": recurrence,
        "weekdays": weekdays or [],
        "upload": False,
        "created_at": datetime.now().isoformat(),
        "done": False,
    }
    data["scheduled_videos"].append(entry)
    save_schedules(data)
    return entry


def backend_ok(timeout=2.0):
    """True se o backend FastAPI (que dispara agendamentos) estiver no ar."""
    try:
        import urllib.request
        urllib.request.urlopen(API_HEALTH, timeout=timeout)
        return True
    except Exception:
        return False


def remove_schedule(schedule_id):
    data = load_schedules()
    data["scheduled_videos"] = [s for s in data["scheduled_videos"] if s.get("id") != schedule_id]
    save_schedules(data)


def mark_schedule_done(schedule_id):
    data = load_schedules()
    for s in data["scheduled_videos"]:
        if s.get("id") == schedule_id:
            s["done"] = True
    save_schedules(data)


# ----------------------------------------------------------- nav item ---

class NavItem(tk.Canvas):
    def __init__(self, master, text, command, right="", dot=None, bg=None):
        super().__init__(master, height=P(34), width=P(10), bg=bg or T["sidebar"], highlightthickness=0, bd=0,
                         cursor="hand2")
        self.name, self.cmd, self.right, self.dot = text, command, right, dot
        self.sel, self.hov, self.badge = False, False, False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set(hov=True))
        self.bind("<Leave>", lambda e: self._set(hov=False))
        self.bind("<Button-1>", lambda e: self.cmd())

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self._draw()

    def set_selected(self, on):
        self._set(sel=on)

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20:
            return
        self.delete("all")
        if self.sel:
            rr(self, P(2), 0, w - P(2), h, P(9), fill=T["nav_sel"], outline="")
        elif self.hov:
            rr(self, P(2), 0, w - P(2), h, P(9), fill=mix(T["sidebar"], T["text"], 0.06), outline="")
        x = P(14)
        if self.dot:
            self.create_oval(x, h / 2 - P(3), x + P(6), h / 2 + P(3), fill=self.dot, outline="")
            x += P(16)
        f = fnt(10, self.sel)
        rw = tkfont.Font(font=fnt(8)).measure(self.right) + P(14) if self.right else 0
        self.create_text(x, h / 2, text=fit_text(self.name, f, w - x - rw - P(10)), anchor="w", font=f,
                         fill=T["accent"] if self.sel else T["text"])
        if self.right:
            self.create_text(w - P(12), h / 2, text=self.right, anchor="e", font=fnt(8), fill=T["text3"])
        if self.badge:
            self.create_oval(w - P(18), h / 2 - P(4), w - P(10), h / 2 + P(4), fill=T["accent"], outline="")


class PhaseChip(tk.Canvas):
    def __init__(self, master, key, title, sub, command, bg=None):
        super().__init__(master, height=P(60), width=P(10), bg=bg or T["card"], highlightthickness=0, bd=0)
        self.key, self.ttl, self.subt, self.cmd = key, title, sub, command
        self.run, self.status, self.inter, self.skip, self.hov = True, "", False, False, False
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<Button-1>", lambda e: self.cmd(self.key) if self.inter else None)

    def _hover(self, on):
        self.hov = on and self.inter
        self.draw()

    def set_state(self, run, status, inter, skip):
        self.run, self.status, self.inter, self.skip = run, status, inter, skip
        self.configure(cursor="hand2" if inter else "arrow")
        self.draw()

    def draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 30:
            return
        self.delete("all")
        if self.run:
            fill, out = T["chip_on"], T["accent"]
        else:
            fill, out = (T["fill_h"] if self.hov else T["fill"]), (T["fill_h"] if self.hov else T["fill"])
        if self.hov and self.run:
            out = T["accent_h"]
        rr(self, 1, 1, w - 1, h - 1, P(12), fill=fill, outline=out)
        self.create_text(P(14), P(20), text=self.ttl, anchor="w", font=fnt(10, True),
                         fill=T["text"] if self.run else T["text3"])
        sub, col = self.subt, T["text2"] if self.run else T["text3"]
        if self.skip:
            sub, col = "Será pulada", T["err"]
        self.create_text(P(14), P(40), text=fit_text(sub, fnt(8), w - P(28)), anchor="w", font=fnt(8), fill=col)
        cx, cy, r = w - P(18), P(18), P(8)
        if self.status == "done":
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=T["ok"], outline="")
            self.create_line(cx - P(3.5), cy, cx - P(1), cy + P(3), cx + P(4), cy - P(3), fill="#FFFFFF",
                             width=max(1, P(2)), capstyle="round", joinstyle="round")
        elif self.status == "running":
            c = T["accent"] if PULSE[0] else mix(T["accent"], fill, 0.5)
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=c, width=max(2, P(2)))
            self.create_oval(cx - P(3), cy - P(3), cx + P(3), cy + P(3), fill=c, outline="")


class Collapsible:
    def __init__(self, parent, title, bg=None):
        bg = bg or T["card"]
        self.frame = tk.Frame(parent, bg=bg)
        head = tk.Frame(self.frame, bg=bg, cursor="hand2")
        head.pack(fill="x")
        self.chev = lbl(head, "▸", 10, False, "text2", bg)
        self.chev.pack(side="left")
        self.t = lbl(head, title, 11, True, "text", bg)
        self.t.pack(side="left", padx=(P(8), 0))
        self.sum = lbl(head, "", 9, False, "text2", bg)
        self.sum.pack(side="right")
        for w in (head, self.chev, self.t, self.sum):
            w.bind("<Button-1>", self.toggle)
        self.body = tk.Frame(self.frame, bg=bg)
        self.open = False

    def set_summary(self, text):
        self.sum.configure(text=text)

    def toggle(self, e=None):
        self.open = not self.open
        if self.open:
            self.body.pack(fill="x", pady=(P(14), 0))
        else:
            self.body.pack_forget()
        self.chev.configure(text="▾" if self.open else "▸")


class ScrollFrame(tk.Frame):
    def __init__(self, master, bg, sb_style):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, yscrollincrement=P(24))
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style=sb_style)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.sb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))

    def wheel(self, n):
        if self.inner.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(n, "units")


def make_field(parent, var, width=None, mono=False, bg=None):
    box = tk.Frame(parent, bg=T["field"], highlightthickness=1, highlightbackground=T["border"],
                   highlightcolor=T["accent"])
    ent = tk.Entry(box, textvariable=var, relief="flat", bd=0, bg=T["field"], fg=T["text"],
                   insertbackground=T["text"], font=fnt(10, False, mono), highlightthickness=0,
                   selectbackground=T["accent"], selectforeground="#FFFFFF", width=width or 1)
    ent.pack(fill="x", padx=P(10), pady=P(7))
    ent.bind("<FocusIn>", lambda e: box.configure(highlightbackground=T["accent"]))
    ent.bind("<FocusOut>", lambda e: box.configure(highlightbackground=T["border"]))
    return box


def labeled(parent, text, widget_factory):
    f = tk.Frame(parent, bg=T["card"])
    lbl(f, text, 9, True, "text2").pack(anchor="w", pady=(0, P(4)))
    widget_factory(f).pack(fill="x")
    return f


def switch_row(parent, title, sub, var):
    f = tk.Frame(parent, bg=T["card"])
    left = tk.Frame(f, bg=T["card"])
    left.pack(side="left", fill="x", expand=True)
    lbl(left, title, 10, True).pack(anchor="w")
    lbl(left, sub, 9, False, "text2").pack(anchor="w")
    Switch(f, var).pack(side="right", padx=(P(12), 0))
    return f


# -------------------------------------------------------------------- app ---
class App(tk.Tk):
    def __init__(self, theme="auto", prompt=None):
        global SCALE, ZOOM_IDX, T
        super().__init__()
        try:
            self.tk.call("encoding", "system", "utf-8")
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
            SCALE = max(1.0, min(3.0, self.winfo_fpixels("1i") / 96.0))
        else:
            SCALE = 1.0
        T.update(DARK if (theme == "dark" or (theme == "auto" and detect_dark())) else LIGHT)
        init_fonts(self)
        self.title("Videomaker — Estúdio de Vídeo Premium")
        self.configure(bg=T["bg"])
        w, h = P(1280), P(860)
        x, y = max(0, (self.winfo_screenwidth() - w) // 2), max(0, (self.winfo_screenheight() - h) // 3)
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.minsize(P(1100), P(720))

        # estado de execucao
        self.q = queue.Queue()
        self.proc = None
        self.running = False
        self.task = ""
        self.plan = None
        self.up_pct = None
        self.stopping = False
        self.then_upload = False
        self.run_started = 0.0
        self.slug_override = None
        self._loaded_prompt = ""
        self.ph = False
        self._toast = None
        self._chips_job = None
        self.from_idx = 0
        self.only_set, self.skip_set = set(), set()
        self.extra = None
        self.page = "create"
        self._link = None

        # variaveis de configuracao
        self.v_mode = tk.StringVar(value="auto")
        self.v_force = tk.BooleanVar(value=False)
        self.v_nopar = tk.BooleanVar(value=False)
        self.v_skipchk = tk.BooleanVar(value=False)
        self.v_dur = tk.IntVar(value=590)
        self.v_voice = tk.StringVar(value="pt-BR-ThalitaNeural")
        self.v_rate = tk.StringVar(value="+12%")
        self.v_pitch = tk.StringVar(value="+8Hz")
        self.v_style = tk.StringVar(value="excited")
        self.v_narr_provider = tk.StringVar(value="gemini")
        self.v_wait = tk.StringVar(value="240")
        self.v_yt_mode = tk.StringVar(value="manual")
        self.v_yt_priv = tk.StringVar(value="private")
        self.v_yt_kids = tk.BooleanVar(value=False)
        self.v_yt_title = tk.StringVar()
        self.v_yt_tags = tk.StringVar(value="pixel art,animação")
        self.v_yt_cat = tk.StringVar(value="24")
        self.v_yt_video = tk.StringVar()
        self.v_yt_thumb = tk.StringVar()
        self.v_yt_when = tk.StringVar()
        self.v_yt_secret = tk.StringVar(value=str(HERE / "client_secret.json"))
        self.v_zoom = tk.StringVar(value="100%")
        self.v_theme = tk.StringVar(value=theme)

        self.saved = {"duration": self.v_dur, "voice": self.v_voice, "rate": self.v_rate, "pitch": self.v_pitch,
                      "style": self.v_style, "wait": self.v_wait, "yt_mode": self.v_yt_mode,
                      "yt_priv": self.v_yt_priv, "yt_kids": self.v_yt_kids, "yt_tags": self.v_yt_tags,
                      "yt_cat": self.v_yt_cat, "yt_secret": self.v_yt_secret, "zoom": self.v_zoom,
                      "theme": self.v_theme}
        self.load_settings()
        ZOOM_IDX = ZOOM_LEVELS.index(float(self.v_zoom.get().rstrip("%")) / 100.0) \
            if self.v_zoom.get().rstrip("%").replace(".", "", 1).isdigit() else ZOOM_IDX_DEFAULT

        self._styles()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()
        self._wire()
        if prompt:
            self.set_prompt(prompt)
        self.show_page("create")
        self.refresh_projects()
        self.refresh_chips()
        self.update_yt_info()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", lambda e: self._wheel(e, -1))
        self.bind_all("<Button-5>", lambda e: self._wheel(e, 1))
        self.bind_all("<Control-Return>", lambda e: self.run_pipeline("full"))
        self.bind_all("<Control-KP_Add>", lambda e: self.zoom_in())
        self.bind_all("<Control-KP_Subtract>", lambda e: self.zoom_out())
        self.bind_all("<Control-KP_0>", lambda e: self.zoom_reset())
        self.after(60, self._drain)
        self.after(1200, self._poll)
        self.after(500, self._pulse)

    # ---------------------------------------------------------- estilos ---
    def _styles(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
            for name, trough in (("Slim", T["bg"]), ("Log", T["log_bg"])):
                s = "%s.Vertical.TScrollbar" % name
                st.layout(s, [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
                    ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
                st.configure(s, troughcolor=trough, background=T["border2"], bordercolor=trough,
                             lightcolor=T["border2"], darkcolor=T["border2"], gripcount=0, width=P(8))
                st.map(s, background=[("active", T["text3"])])
        except tk.TclError:
            pass

    # ------------------------------------------------------------- zoom ---
    def zoom_in(self):
        global ZOOM_IDX
        if ZOOM_IDX < len(ZOOM_LEVELS) - 1:
            ZOOM_IDX += 1
            self._apply_zoom()

    def zoom_out(self):
        global ZOOM_IDX
        if ZOOM_IDX > 0:
            ZOOM_IDX -= 1
            self._apply_zoom()

    def zoom_reset(self):
        global ZOOM_IDX
        ZOOM_IDX = ZOOM_IDX_DEFAULT
        self._apply_zoom()

    def _apply_zoom(self):
        pct = int(ZOOM_LEVELS[ZOOM_IDX] * 100)
        self.v_zoom.set("%d%%" % pct)
        self._refresh_zoom_buttons()
        self.after_idle(self._rebuild_ui)

    def _refresh_zoom_buttons(self):
        for name, btn in getattr(self, "_zoom_btns", {}).items():
            active = (name == str(ZOOM_IDX))
            btn.set_enabled(True)
            btn._font = fnt(10, True)
            btn._draw()

    def _rebuild_ui(self):
        """Recria a interface com o novo zoom."""
        self.destroy_pages()
        self._build_main()
        self._wire()
        self.show_page(self.page)
        self.refresh_projects()
        self.refresh_chips()
        self.update_yt_info()

    def destroy_pages(self):
        for p in list(self.pages.values()):
            try:
                p.pack_forget()
                p.destroy()
            except tk.TclError:
                pass
        self.pages = {}

    # ------------------------------------------------------------- sidebar ---
    def _build_sidebar(self):
        sb = tk.Frame(self, bg=T["sidebar"], width=P(250))
        sb.grid(row=0, column=0, sticky="ns")
        sb.pack_propagate(False)
        brand = tk.Frame(sb, bg=T["sidebar"])
        brand.pack(fill="x", padx=P(20), pady=(P(28), P(26)))
        logo = tk.Canvas(brand, width=P(36), height=P(36), bg=T["sidebar"], highlightthickness=0, bd=0)
        rr(logo, 0, 0, P(36), P(36), P(10), fill=T["accent"], outline="")
        logo.create_oval(P(9), P(9), P(27), P(27), fill="#FFFFFF", outline="")
        logo.create_text(P(18), P(18), text="V", fill=T["accent"], font=fnt(14, True))
        logo.pack(side="left")
        names = tk.Frame(brand, bg=T["sidebar"])
        names.pack(side="left", padx=(P(12), 0))
        lbl(names, "Videomaker", 14, True, bg=T["sidebar"]).pack(anchor="w")
        lbl(names, "Estúdio de vídeo v3", 8, False, "text2", T["sidebar"]).pack(anchor="w")

        self.nav = {}
        for key in ("create", "publish", "daily", "executivo", "activity", "settings"):
            n = NavItem(sb, PAGE_TEXT[key][0], lambda k=key: self.show_page(k))
            n.pack(fill="x", padx=P(8), pady=1)
            self.nav[key] = n

        # zoom na sidebar inferior
        zb = tk.Frame(sb, bg=T["sidebar"])
        zb.pack(side="bottom", fill="x", padx=P(20), pady=P(24))
        lbl(zb, "Zoom da interface", 8, True, "text3", T["sidebar"]).pack(anchor="w", pady=(0, P(6)))
        row = tk.Frame(zb, bg=T["sidebar"])
        row.pack(fill="x")
        self._zoom_btns = {}
        for i, z in enumerate(ZOOM_LEVELS):
            pct = int(z * 100)
            b = Button(row, "%d%%" % pct, lambda i=i: self._set_zoom(i), "ghost", h=26, padx=10, size=8)
            b.pack(side="left", padx=(0, P(4)))
            self._zoom_btns[str(i)] = b
        self._refresh_zoom_buttons()
        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=P(16), pady=P(10))
        lbl(sb, "AJUSTES", 8, True, "text3", T["sidebar"]).pack(anchor="w", padx=P(20), pady=(0, P(6)))
        self.proj_box = tk.Frame(sb, bg=T["sidebar"])
        self.proj_box.pack(fill="x", padx=P(8))

    def _set_zoom(self, idx):
        global ZOOM_IDX
        ZOOM_IDX = idx
        self._apply_zoom()

    # ------------------------------------------------------------- main ---
    def _build_main(self):
        self.main = tk.Frame(self, bg=T["bg"])
        self.main.grid(row=0, column=1, sticky="nsew")

        # barra de acao (fixa, embaixo)
        bar = tk.Frame(self.main, bg=T["card"])
        bar.pack(side="bottom", fill="x")
        tk.Frame(self.main, bg=T["border"], height=1).pack(side="bottom", fill="x")
        inner = tk.Frame(bar, bg=T["card"])
        inner.pack(fill="x", padx=P(32), pady=P(14))
        left = tk.Frame(inner, bg=T["card"])
        left.pack(side="left", fill="x", expand=True, padx=(0, P(24)))
        self.st_text = lbl(left, "Pronto", 10, True)
        self.st_text.pack(anchor="w", pady=(0, P(6)))
        self.progress = ProgressBar(left, bg=T["card"])
        self.progress.pack(fill="x")
        right = tk.Frame(inner, bg=T["card"])
        right.pack(side="right")
        self.btn_extra = Button(right, "Abrir", None, "ghost")
        self.btn_stop = Button(right, "Parar", self.stop_run, "danger")
        self.btn_stop_all = Button(right, "Parar tudo", self.stop_all, "danger")
        self.btn_resume = Button(right, "Retomar", lambda: self.run_pipeline("resume"))
        self.btn_run = Button(right, "Gerar vídeo", lambda: self.run_pipeline("full"), "primary",
                              padx=24, icon="▶")
        self.btn_extra.pack(side="left")
        self.btn_stop.pack(side="left", padx=(0, P(8)))
        self.btn_stop_all.pack(side="left", padx=(0, P(8)))
        self.btn_resume.pack(side="left", padx=(0, P(8)))
        self.btn_run.pack(side="left")

        # cabecalho
        hdr = tk.Frame(self.main, bg=T["bg"])
        hdr.pack(side="top", fill="x", padx=P(32), pady=(P(28), P(14)))
        titles = tk.Frame(hdr, bg=T["bg"])
        titles.pack(side="left")
        self.h_title = lbl(titles, "Criar", 26, True, bg=T["bg"])
        self.h_title.pack(anchor="w")
        self.h_sub = lbl(titles, "", 10, False, "text2", T["bg"])
        self.h_sub.pack(anchor="w", pady=(P(2), 0))
        self.pill = StatusPill(hdr)
        self.pill.pack(side="right")

        # paginas
        self.pages = {}
        host = tk.Frame(self.main, bg=T["bg"])
        host.pack(side="top", fill="both", expand=True)
        self.host = host
        self.pages["create"] = ScrollFrame(host, T["bg"], "Slim.Vertical.TScrollbar")
        self.pages["publish"] = ScrollFrame(host, T["bg"], "Slim.Vertical.TScrollbar")
        self.pages["daily"] = ScrollFrame(host, T["bg"], "Slim.Vertical.TScrollbar")
        self.pages["executivo"] = ScrollFrame(host, T["bg"], "Slim.Vertical.TScrollbar")
        self.pages["activity"] = tk.Frame(host, bg=T["bg"])
        self.pages["settings"] = tk.Frame(host, bg=T["bg"])
        self._page_create(self.pages["create"].inner)
        self._page_publish(self.pages["publish"].inner)
        self._page_daily(self.pages["daily"].inner)
        self._page_executivo(self.pages["executivo"].inner)
        self._page_activity(self.pages["activity"])
        self._page_settings(self.pages["settings"])

    # ---------------------------------------------------------- criar ---
    def _page_create(self, root):
        M = P(32)
        c = Card(root, elevated=True)
        c.pack(fill="x", padx=M, pady=(P(4), P(16)))
        b = c.body
        lbl(b, "Sobre o que é o vídeo?", 14, True).pack(anchor="w")
        lbl(b, "Descreva o tema. O nome do projeto é gerado automaticamente.", 9, False, "text2").pack(
            anchor="w", pady=(P(2), P(12)))
        box = tk.Frame(b, bg=T["field"], highlightthickness=1, highlightbackground=T["border"],
                       highlightcolor=T["accent"])
        box.pack(fill="x")
        self.prompt = tk.Text(box, height=4, wrap="word", relief="flat", bd=0, bg=T["field"], fg=T["text"],
                              insertbackground=T["text"], font=fnt(12), padx=P(12), pady=P(10), width=1,
                              highlightthickness=0, selectbackground=T["accent"], selectforeground="#FFFFFF",
                              undo=True)
        self.prompt.pack(fill="x")
        self.prompt.bind("<FocusIn>", lambda e: (self._p_in(), box.configure(highlightbackground=T["accent"])))
        self.prompt.bind("<FocusOut>", lambda e: (self._p_out(), box.configure(highlightbackground=T["border"])))
        self.prompt.bind("<KeyRelease>", self.on_prompt_change)
        self.prompt.bind("<Control-Return>", lambda e: (self.run_pipeline("full"), "break")[1])
        self._p_out()

        row = tk.Frame(b, bg=T["card"])
        row.pack(fill="x", pady=(P(12), 0))
        lbl(row, "Projeto", 9, False, "text2").pack(side="left")
        self.slug_lbl = tk.Label(row, text="—", font=fnt(9, False, True), fg=T["text"], bg=T["fill"],
                                 padx=P(10), pady=P(3))
        self.slug_lbl.pack(side="left", padx=P(8))

        tk.Frame(b, bg=T["border"], height=1).pack(fill="x", pady=P(18))
        drow = tk.Frame(b, bg=T["card"])
        drow.pack(fill="x")
        lbl(drow, "Duração alvo", 10, True).pack(side="left")
        self.dur_lbl = lbl(drow, fmt_dur(self.v_dur.get()), 11, True, "accent")
        self.dur_lbl.pack(side="right")
        Slider(b, self.v_dur, 30, 1200, 10).pack(fill="x", pady=(P(6), P(8)))
        pre = tk.Frame(b, bg=T["card"])
        pre.pack(fill="x")
        for label, secs in (("3 min", 180), ("5 min", 300), ("10 min", 590), ("15 min", 900)):
            Button(pre, label, lambda s=secs: self.v_dur.set(s), "secondary", h=28, padx=14, size=9).pack(
                side="left", padx=(0, P(8)))

        c2 = Card(root, elevated=True)
        c2.pack(fill="x", padx=M, pady=(0, P(16)))
        b = c2.body
        head = tk.Frame(b, bg=T["card"])
        head.pack(fill="x")
        ttl = tk.Frame(head, bg=T["card"])
        ttl.pack(side="left")
        lbl(ttl, "Etapas", 14, True).pack(anchor="w")
        lbl(ttl, "Escolha como o pipeline deve rodar.", 9, False, "text2").pack(anchor="w", pady=(P(2), 0))
        Segmented(head, RUN_MODES, self.v_mode).pack(side="right")
        self.summary = lbl(b, "", 9, False, "text2", justify="left", anchor="w")
        self.summary.pack(fill="x", pady=(P(14), P(12)))
        grid = tk.Frame(b, bg=T["card"])
        grid.pack(fill="x")
        self.chips = []
        for i, (k, name, sub) in enumerate(PHASES):
            chip = PhaseChip(grid, k, name, sub, self.chip_click)
            chip.grid(row=i // 5, column=i % 5, sticky="ew", padx=(0 if i % 5 == 0 else P(5), 0 if i % 5 == 4
                                                                    else P(5)), pady=P(5))
            self.chips.append((k, chip))
        for col in range(5):
            grid.grid_columnconfigure(col, weight=1, uniform="chips")
        tk.Frame(b, bg=T["border"], height=1).pack(fill="x", pady=P(18))
        sw = tk.Frame(b, bg=T["card"])
        sw.pack(fill="x")
        switch_row(sw, "Sem paralelismo", "Roda uma etapa por vez", self.v_nopar).pack(
            side="left", fill="x", expand=True)
        switch_row(sw, "Pular lint no render", "-SkipCheck (re-render rápido)", self.v_skipchk).pack(
            side="left", fill="x", expand=True)

        c3 = Card(root, elevated=True)
        c3.pack(fill="x", padx=M, pady=(0, P(24)))
        self.voice_box = Collapsible(c3.body, "Voz e ajustes avançados")
        self.voice_box.frame.pack(fill="x")
        vb = self.voice_box.body
        for col, w in enumerate((3, 1, 1, 1, 1)):
            vb.grid_columnconfigure(col, weight=w, uniform="v")
        prov_row = tk.Frame(vb, bg=T["card"])
        prov_row.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, P(10)))
        lbl(prov_row, "Motor de narração", 9, True, "text2").pack(side="left")
        Segmented(prov_row, [("gemini", "Gemini"), ("edge", "Edge")],
                  self.v_narr_provider).pack(side="right")
        for col, (name, var, mono) in enumerate((("Voz", self.v_voice, True), ("Velocidade", self.v_rate, True),
                                                 ("Tom", self.v_pitch, True), ("Estilo", self.v_style, False),
                                                 ("Espera máx. (s)", self.v_wait, False))):
            labeled(vb, name, lambda p, v=var, m=mono: make_field(p, v, mono=m)).grid(
                row=1, column=col, sticky="ew", padx=(0, P(10)) if col < 4 else 0)
        lbl(vb, "Gemini: deixe a voz como está para alternar entre Achernar e Leda a cada vídeo; "
                 "ou digite uma voz (ex: Leda, Kore, Zephyr). Edge: use vozes pt-BR-*Neural.",
            8, False, "text2", anchor="w", justify="left").grid(
            row=2, column=0, columnspan=5, sticky="ew", pady=(P(8), 0))

    # -------------------------------------------------------- publicar ---
    def _page_publish(self, root):
        M = P(32)
        c = Card(root, elevated=True)
        c.pack(fill="x", padx=M, pady=(P(4), P(16)))
        b = c.body
        lbl(b, "Envio", 14, True).pack(anchor="w")
        lbl(b, "Quando e com qual visibilidade o vídeo vai para o YouTube.", 9, False, "text2").pack(
            anchor="w", pady=(P(2), P(14)))
        r1 = tk.Frame(b, bg=T["card"])
        r1.pack(fill="x")
        lbl(r1, "Quando enviar", 10, True).pack(side="left")
        Segmented(r1, YT_MODES, self.v_yt_mode).pack(side="right")
        self.yt_mode_help = lbl(b, "", 9, False, "text2", anchor="w", justify="left")
        self.yt_mode_help.pack(fill="x", pady=(P(6), P(14)))
        r2 = tk.Frame(b, bg=T["card"])
        r2.pack(fill="x")
        lbl(r2, "Visibilidade", 10, True).pack(side="left")
        Segmented(r2, YT_PRIVACY, self.v_yt_priv).pack(side="right")
        self.yt_priv_help = lbl(b, "", 9, False, "text2", anchor="w", justify="left")
        self.yt_priv_help.pack(fill="x", pady=(P(6), 0))

        c2 = Card(root, elevated=True)
        c2.pack(fill="x", padx=M, pady=(0, P(16)))
        b = c2.body
        lbl(b, "Vídeo", 14, True).pack(anchor="w", pady=(0, P(14)))
        arq = tk.Frame(b, bg=T["card"])
        arq.pack(fill="x")
        fld = labeled(arq, "Arquivo MP4 (vazio = vídeo do projeto atual)",
                      lambda p: make_field(p, self.v_yt_video))
        fld.pack(side="left", fill="x", expand=True)
        Button(arq, "Escolher…", self.pick_video, "secondary").pack(side="left", padx=(P(10), 0),
                                                                    pady=(P(20), 0))
        self.yt_info = lbl(b, "", 9, False, "text2", anchor="w")
        self.yt_info.pack(fill="x", pady=(P(6), P(14)))
        labeled(b, "Título (vazio = usa o prompt)", lambda p: make_field(p, self.v_yt_title)).pack(fill="x")

        def desc(p):
            box = tk.Frame(p, bg=T["field"], highlightthickness=1, highlightbackground=T["border"],
                           highlightcolor=T["accent"])
            self.yt_desc = tk.Text(box, height=3, wrap="word", relief="flat", bd=0, bg=T["field"], fg=T["text"],
                                   insertbackground=T["text"], font=fnt(10), padx=P(10), pady=P(7), width=1,
                                   highlightthickness=0, selectbackground=T["accent"], selectforeground="#FFFFFF")
            self.yt_desc.pack(fill="x")
            self.yt_desc.bind("<FocusIn>", lambda e: box.configure(highlightbackground=T["accent"]))
            self.yt_desc.bind("<FocusOut>", lambda e: box.configure(highlightbackground=T["border"]))
            return box
        labeled(b, "Descrição (vazio = usa o prompt)", desc).pack(fill="x", pady=(P(12), P(12)))
        labeled(b, "Tags (separadas por vírgula)", lambda p: make_field(p, self.v_yt_tags)).pack(fill="x")

        tk.Frame(b, bg=T["border"], height=1).pack(fill="x", pady=P(18))
        self.more = Collapsible(b, "Mais opções")
        self.more.frame.pack(fill="x")
        mb = self.more.body
        mb.grid_columnconfigure(0, weight=1)
        mb.grid_columnconfigure(1, weight=1)
        labeled(mb, "Categoria (24 = Entretenimento, 1 = Filmes)",
                lambda p: make_field(p, self.v_yt_cat)).grid(row=0, column=0, sticky="ew", padx=(0, P(10)))
        labeled(mb, "Agendar (AAAA-MM-DD HH:MM, hora local)",
                lambda p: make_field(p, self.v_yt_when)).grid(row=0, column=1, sticky="ew")
        th = labeled(mb, "Thumbnail (opcional)", lambda p: make_field(p, self.v_yt_thumb))
        th.grid(row=1, column=0, sticky="ew", padx=(0, P(10)), pady=(P(12), 0))
        Button(mb, "Escolher…", self.pick_thumb, "secondary").grid(row=1, column=1, sticky="w",
                                                                   pady=(P(32), 0))
        sec = labeled(mb, "Credenciais OAuth (client_secret.json)",
                      lambda p: make_field(p, self.v_yt_secret))
        sec.grid(row=2, column=0, sticky="ew", padx=(0, P(10)), pady=(P(12), 0))
        Button(mb, "Escolher…", self.pick_secret, "secondary").grid(row=2, column=1, sticky="w",
                                                                    pady=(P(32), 0))
        switch_row(mb, "Feito para crianças", "Exigido pelo YouTube; confira se se aplica ao canal",
                   self.v_yt_kids).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(P(16), 0))

        foot = tk.Frame(b, bg=T["card"])
        foot.pack(fill="x", pady=(P(20), 0))
        lbl(foot, "No primeiro envio o navegador abre para você autorizar o canal.", 9, False, "text3").pack(
            side="left")
        self.btn_upload = Button(foot, "Enviar ao YouTube", self.run_upload, "primary", padx=22,
                                 icon="↗")
        self.btn_upload.pack(side="right")
        tk.Frame(root, bg=T["bg"], height=P(24)).pack()

    # ------------------------------------------------------- diario ---
    def _page_daily(self, root):
        M = P(32)

        # --- executor diario (mantido) ---
        c = Card(root, elevated=True)
        c.pack(fill="x", padx=M, pady=(P(4), P(16)))
        b = c.body
        lbl(b, "Executor Diário", 14, True).pack(anchor="w")
        lbl(b, "Gera um vídeo por dia a partir da fila de tópicos em scripts/topics.txt.",
            9, False, "text2").pack(anchor="w", pady=(P(2), P(14)))

        row = tk.Frame(b, bg=T["card"])
        row.pack(fill="x", pady=(0, P(12)))
        Button(row, "Status da fila", self.daily_status, "secondary", icon="📋").pack(side="left",
                                                                                   padx=(0, P(8)))
        Button(row, "Executar agora", self.daily_run, "primary", icon="▶").pack(side="left",
                                                                                padx=(0, P(8)))
        Button(row, "Simulação (dry-run)", self.daily_dry, "ghost", icon="🔍").pack(side="left",
                                                                                   padx=(0, P(8)))
        Button(row, "Não enviar", self.daily_no_upload, "secondary", icon="🎬").pack(side="left",
                                                                                    padx=(0, P(8)))
        Button(row, "Forçar hoje", self.daily_force, "secondary", icon="⚡").pack(side="left")

        row2 = tk.Frame(b, bg=T["card"])
        row2.pack(fill="x", pady=(P(16), 0))
        Button(row2, "Liberar fila", self.daily_unpause, "secondary", icon="🔓").pack(side="left",
                                                                                      padx=(0, P(8)))
        Button(row2, "Reenviar falhos", lambda: self.daily_unpause(True), "secondary",
               icon="🔄").pack(side="left", padx=(0, P(8)))
        Button(row2, "Parar agente", self.stop_agent, "danger", icon="⏹").pack(side="left")

        self.daily_status_lbl = lbl(b, "", 9, False, "text2", anchor="w", justify="left")
        self.daily_status_lbl.pack(fill="x", pady=(P(16), P(12)))
        self.backend_lbl = lbl(b, "", 9, False, "text2", anchor="w")
        self.backend_lbl.pack(fill="x", pady=(0, P(8)))
        self._refresh_backend_lbl()
        self.daily_status()

        # --- calendario de agendamento ---
        c2 = Card(root, elevated=True)
        c2.pack(fill="x", padx=M, pady=(0, P(24)))
        b2 = c2.body
        hdr = tk.Frame(b2, bg=T["card"])
        hdr.pack(fill="x", pady=(0, P(12)))
        lbl(hdr, "Calendário de Agendamento", 13, True).pack(side="left")
        lbl(hdr, "Agende vídeos para datas específicas, vários por dia ou recorrência semanal.",
            9, False, "text2").pack(side="right", anchor="e")

        self.cal_events_by_date = {}
        self.cal_selected_date = None
        self.cal_date_lbl = None
        self.cal_list = None
        self.new_date_var = None
        self.new_time_var = None
        self.new_prompt_txt = None
        self.new_rec_var = None

        split = tk.Frame(b2, bg=T["card"])
        split.pack(fill="both", expand=True)

        # esquerda: calendario mensal
        left = tk.Frame(split, bg=T["card"])
        left.pack(side="left", fill="y", padx=(0, P(12)))

        self.cal_header = CalendarHeader(left, self.cal_prev, self.cal_next, self.cal_today, "")
        self.cal_header.pack(fill="x", pady=(0, P(8)))
        self.cal_month = CalendarMonth(left, self.cal_events_by_date, self.cal_on_day_selected)
        self.cal_month.pack(fill="y")

        # direita: detalhes do dia + novo agendamento
        right = tk.Frame(split, bg=T["card"])
        right.pack(side="left", fill="both", expand=True)

        # detalhes do dia selecionado
        det = Card(right, elevated=False, fill=T["fill"], outline=T["border"], autoheight=False)
        det.pack(fill="x", pady=(0, P(16)))
        db = det.body
        self.cal_date_lbl = lbl(db, "Selecione um dia no calendário", 12, True)
        self.cal_date_lbl.pack(anchor="w", pady=(P(10), P(8)))
        self.cal_list = tk.Frame(db, bg=T["fill"])
        self.cal_list.pack(fill="x", pady=(0, P(10)))

        # novo agendamento
        novo = Card(right, elevated=True)
        novo.pack(fill="x")
        nb = novo.body
        lbl(nb, "Agendar novo vídeo", 12, True).pack(anchor="w", pady=(P(10), P(12)))

        form = tk.Frame(nb, bg=T["card"])
        form.pack(fill="x", pady=(0, P(10)))

        # linha 1: data e hora
        r1 = tk.Frame(form, bg=T["card"])
        r1.pack(fill="x", pady=(0, P(8)))
        c1 = tk.Frame(r1, bg=T["card"])
        c1.pack(side="left", fill="x", expand=True, padx=(0, P(8)))
        lbl(c1, "Data", 9, False, "text2").pack(anchor="w")
        self.new_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.new_date_ent = tk.Entry(c1, textvariable=self.new_date_var, font=fnt(10),
                                     bg=T["field"], fg=T["text"], insertbackground=T["text"],
                                     relief="flat", bd=0)
        self.new_date_ent.pack(fill="x", pady=(P(4), 0), ipady=P(6))

        c2f = tk.Frame(r1, bg=T["card"])
        c2f.pack(side="left", fill="x", expand=True, padx=(P(8), 0))
        lbl(c2f, "Hora", 9, False, "text2").pack(anchor="w")
        self.new_time_var = tk.StringVar(value="09:00")
        self.new_time_ent = tk.Entry(c2f, textvariable=self.new_time_var, font=fnt(10),
                                     bg=T["field"], fg=T["text"], insertbackground=T["text"],
                                     relief="flat", bd=0)
        self.new_time_ent.pack(fill="x", pady=(P(4), 0), ipady=P(6))

        # linha 2: prompt
        lbl(form, "Prompt / tema do vídeo", 9, False, "text2").pack(anchor="w", pady=(0, P(4)))
        self.new_prompt_txt = tk.Text(form, height=3, wrap="word", relief="flat", bd=0,
                                      bg=T["field"], fg=T["text"], insertbackground=T["text"],
                                      font=fnt(10), padx=P(10), pady=P(8), highlightthickness=0)
        self.new_prompt_txt.pack(fill="x", pady=(0, P(8)))

        # linha 3: recorrencia
        r3 = tk.Frame(form, bg=T["card"])
        r3.pack(fill="x", pady=(0, P(10)))
        lbl(r3, "Recorrência", 9, False, "text2").pack(side="left", padx=(0, P(8)))
        self.new_rec_var = tk.StringVar(value="none")
        rec_opts = [("none", "Não repetir"), ("daily", "Todos os dias"),
                    ("weekdays", "Dias úteis"), ("weekly", "Semanal")]
        for i, (val, lab) in enumerate(rec_opts):
            rb = tk.Radiobutton(r3, text=lab, variable=self.new_rec_var, value=val,
                                bg=T["card"], fg=T["text"], selectcolor=T["fill"],
                                font=fnt(9), activebackground=T["card"], activeforeground=T["text"])
            rb.pack(side="left", padx=(0, P(16)))

        btn_row = tk.Frame(nb, bg=T["card"])
        btn_row.pack(fill="x", pady=(P(4), P(14)))
        Button(btn_row, "Agendar", self.cal_add_schedule, "primary", icon="+").pack(side="left")
        Button(btn_row, "Limpar", self.cal_clear_form, "ghost", icon="🗑").pack(side="left",
                                                                                padx=(P(8), 0))

        self.cal_refresh()

        # --- topicos da fila (mantido) ---
        c3 = Card(root, elevated=True)
        c3.pack(fill="x", padx=M, pady=(0, P(24)))
        b3 = c3.body
        lbl(b3, "Tópicos da fila (próximos)", 13, True).pack(anchor="w")
        self.daily_list = tk.Frame(b3, bg=T["card"])
        self.daily_list.pack(fill="x", pady=(P(10), 0))
        self.refresh_daily_list()

    # ----------------------------------------- painel executivo ---
    def _page_executivo(self, root):
        M = P(32)

        c = Card(root, elevated=True)
        c.pack(fill="x", padx=M, pady=(P(4), P(16)))
        b = c.body
        head = tk.Frame(b, bg=T["card"])
        head.pack(fill="x", pady=(P(10), P(12)))
        ttl = tk.Frame(head, bg=T["card"])
        ttl.pack(side="left")
        lbl(ttl, "Painel Executivo", 14, True).pack(anchor="w")
        lbl(ttl, "Telemetria local: KPIs, fases, próximos disparos e agentes.", 9, False, "text2").pack(anchor="w")
        btns = tk.Frame(head, bg=T["card"])
        btns.pack(side="right")
        Button(btns, "Atualizar", self.update_executivo, "secondary", icon="↻").pack(side="left",
                                                                                     padx=(0, P(8)))
        Button(btns, "Parar agente", self.stop_agent, "ghost", icon="⏹").pack(side="left",
                                                                              padx=(0, P(8)))
        Button(btns, "Parar tudo", self.stop_all, "danger", icon="⛔").pack(side="left")

        # KPIs
        krow = tk.Frame(b, bg=T["card"])
        krow.pack(fill="x", pady=(P(4), P(10)))
        self.kpi_vars = {
            "total": tk.StringVar(value="—"),
            "done": tk.StringVar(value="—"),
            "rate": tk.StringVar(value="—"),
            "avg": tk.StringVar(value="—"),
            "next": tk.StringVar(value="—"),
        }
        tiles = (
            ("Projetos", "total", "accent"),
            ("Concluídos", "done", "ok"),
            ("Sucesso", "rate", "accent"),
            ("Duração média", "avg", "text"),
            ("Próximo disparo", "next", "warn"),
        )
        for title, key, col in tiles:
            box = tk.Frame(krow, bg=T["fill"], highlightthickness=1, highlightbackground=T["border"])
            box.pack(side="left", fill="x", expand=True, padx=(0, P(8)))
            lbl(box, title, 8, True, "text2", T["fill"]).pack(anchor="w", padx=P(12), pady=(P(8), 0))
            tk.Label(box, textvariable=self.kpi_vars[key], font=fnt(16, True),
                     fg=T[col], bg=T["fill"]).pack(anchor="w", padx=P(12), pady=(0, P(10)))

        self.agent_banner = lbl(b, "Agentes externos: —", 9, False, "text2")
        self.agent_banner.pack(anchor="w", pady=(P(4), P(10)))

        # Fases do último/run
        lbl(b, "Fases do projeto recente", 12, True).pack(anchor="w", pady=(P(6), P(6)))
        self.phase_rows = {}
        grid = tk.Frame(b, bg=T["card"])
        grid.pack(fill="x")
        for i, (key, name, _sub) in enumerate(PHASES):
            row = tk.Frame(grid, bg=T["card"])
            row.grid(row=i // 5, column=i % 5, sticky="ew", padx=P(4), pady=P(4))
            grid.grid_columnconfigure(i % 5, weight=1)
            dot = tk.Canvas(row, width=P(10), height=P(10), bg=T["card"], highlightthickness=0, bd=0)
            dot.pack(side="left")
            lbl(row, name, 9, False).pack(side="left", padx=(P(6), 0))
            self.phase_rows[key] = dot

        self.exec_slug = lbl(b, "", 9, False, "text2")
        self.exec_slug.pack(anchor="w", pady=(P(10), 0))
        self.update_executivo()

    def _agent_pids(self):
        """PIDs de processos python externos rodando daily_runner/pipeline."""
        try:
            ps = [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
                "Where-Object { $_.CommandLine -match 'daily_runner\\.py|pipeline\\.py' } | "
                "Select-Object -ExpandProperty ProcessId"
            ]
            r = subprocess.run(ps, capture_output=True, text=True, timeout=10,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            return [int(x) for x in r.stdout.split() if x.strip().isdigit()]
        except Exception:
            return []

    def _kill_pid_tree(self, pid):
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            return True
        except Exception:
            return False

    def update_executivo(self):
        if not hasattr(self, "kpi_vars"):
            return
        items = list_projects()
        total = len(items)
        done_n = sum(1 for it in items if it["video"])
        rate = round(done_n / total * 100, 1) if total else 0.0
        self.kpi_vars["total"].set(str(total))
        self.kpi_vars["done"].set(str(done_n))
        self.kpi_vars["rate"].set("%s%%" % rate)

        # duração média aproximada: mtime do project.json ao vídeo (fallback: —)
        durs = []
        recent = None
        for it in items:
            slug = it["slug"]
            try:
                st = load_state(slug)
                ph = st.get("phases") or {}
                tss = sorted(v.get("ts") for v in ph.values()
                             if isinstance(v, dict) and v.get("ts"))
                if len(tss) >= 2:
                    d0 = datetime.strptime(tss[0], "%Y-%m-%d %H:%M:%S")
                    d1 = datetime.strptime(tss[-1], "%Y-%m-%d %H:%M:%S")
                    durs.append((d1 - d0).total_seconds())
            except Exception:
                pass
            if recent is None or it["mtime"] > recent[0]:
                recent = (it["mtime"], it)
        if durs:
            avg = sum(durs) / len(durs)
            self.kpi_vars["avg"].set(fmt_dur(avg))
        else:
            self.kpi_vars["avg"].set("—")

        # próximo disparo
        now = datetime.now()
        nxt = None
        try:
            data = load_schedules()
            for s in data.get("scheduled_videos", []):
                if s.get("done"):
                    continue
                try:
                    dt = datetime.strptime("%s %s" % (s.get("date"), s.get("time")), "%Y-%m-%d %H:%M")
                except Exception:
                    continue
                if dt < now:
                    continue
                if nxt is None or dt < nxt[0]:
                    nxt = (dt, s)
        except Exception:
            pass
        if nxt:
            delta = int((nxt[0] - now).total_seconds())
            self.kpi_vars["next"].set(fmt_dur(delta))
        else:
            self.kpi_vars["next"].set("—")

        # fases do projeto recente
        for key, dot in self.phase_rows.items():
            dot.delete("all")
            done_set = done_phases(recent[1]["slug"]) if recent else set()
            col = T["ok"] if key in done_set else T["fill_p"]
            rr(dot, 0, 0, P(10), P(10), P(5), fill=col, outline="")
        if recent:
            self.exec_slug.configure(text="Último: %s · %d/%d fases%s" % (
                recent[1]["slug"], recent[1]["done"], len(PHASES),
                " · MP4 pronto" if recent[1]["video"] else ""))
        else:
            self.exec_slug.configure(text="Nenhum projeto ainda")

        # agentes (só consulta quando a página está visível — PowerShell é lento)
        if getattr(self, "page", "") == "executivo":
            pids = self._agent_pids()
            if pids:
                self.agent_banner.configure(
                    text="Agente externo ativo · PIDs %s" % ", ".join(str(p) for p in pids),
                    fg=T["warn"])
            else:
                self.agent_banner.configure(text="Nenhum agente externo detectado", fg=T["text2"])
            self.after(5000, self._exec_tick)
        elif hasattr(self, "agent_banner"):
            self.agent_banner.configure(text="Agentes: abra esta página para consultar", fg=T["text2"])

    def _exec_tick(self):
        if self.page == "executivo":
            self.update_executivo()

    # ----------------------------- calendario callbacks ----------------------
    def cal_refresh(self):
        schedules = load_schedules()
        self.cal_events_by_date = {}
        for s in schedules.get("scheduled_videos", []):
            self.cal_events_by_date.setdefault(s.get("date"), []).append(s)
        self.cal_month.events_by_date = self.cal_events_by_date
        self.cal_month._build()
        if self.cal_month.selected:
            self.cal_on_day_selected(self.cal_month.selected.date)
        else:
            self.cal_clear_detail()

    def cal_prev(self):
        self.cal_month.prev_month()
        self.cal_refresh()

    def cal_next(self):
        self.cal_month.next_month()
        self.cal_refresh()

    def cal_today(self):
        self.cal_month.go_today()
        self.cal_refresh()

    def cal_on_day_selected(self, date_obj):
        if date_obj is None:
            return
        self.cal_selected_date = date_obj
        ds = date_obj.isoformat()
        self.new_date_var.set(ds)
        self.cal_date_lbl.configure(text=date_obj.strftime("%d/%m/%Y - %A"))
        self.cal_show_day_schedules(ds)

    def cal_show_day_schedules(self, date_str):
        for w in self.cal_list.winfo_children():
            w.destroy()
        schedules = load_schedules()
        events = [s for s in schedules.get("scheduled_videos", []) if s.get("date") == date_str]
        if not events:
            lbl(self.cal_list, "Nenhum agendamento para este dia.", 9, False, "text2").pack(
                anchor="w", pady=P(4))
            return
        for s in events:
            done = s.get("done", False)
            dot_col = T["ok"] if done else T["accent"]
            row = tk.Frame(self.cal_list, bg=T["fill"])
            row.pack(fill="x", pady=P(3))
            tk.Frame(row, width=P(3), height=P(14), bg=dot_col).pack(side="left", padx=(P(8), P(8)))
            lbl(row, s.get("time", "--:--"), 9, True).pack(side="left")
            lbl(row, " · " + s.get("prompt", "")[:60], 9, False, "text2").pack(side="left")
            rec = s.get("recurrence", "none")
            if rec != "none":
                lbl(row, " [%s]" % rec, 8, False, "text3").pack(side="left")
            if done:
                lbl(row, "  ✓ concluído", 8, False, T["ok"]).pack(side="left")
            else:
                Button(row, "✕", lambda sid=s.get("id"): self.cal_remove(sid), "danger",
                       h=22, padx=6, size=8).pack(side="right", padx=(P(6), P(8)))

    def cal_clear_detail(self):
        self.cal_selected_date = None
        self.cal_date_lbl.configure(text="Selecione um dia no calendário")
        for w in self.cal_list.winfo_children():
            w.destroy()
        lbl(self.cal_list, "Selecione um dia para ver os agendamentos.", 9, False, "text2").pack(
            anchor="w", pady=P(4))

    def cal_clear_form(self):
        self.new_date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.new_time_var.set("09:00")
        self.new_prompt_txt.delete("1.0", "end")
        self.new_rec_var.set("none")

    def cal_add_schedule(self):
        date_str = self.new_date_var.get().strip()
        time_str = self.new_time_var.get().strip()
        prompt = self.new_prompt_txt.get("1.0", "end").strip()
        rec = self.new_rec_var.get()
        if not date_str or not time_str or not prompt:
            self.toast("Preencha data, hora e prompt.", "err")
            return
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            self.toast("Data ou hora inválida. Use YYYY-MM-DD e HH:MM.", "err")
            return
        entry = add_schedule(date_str, time_str, prompt, rec)
        self.cal_clear_form()
        self.cal_refresh()
        if backend_ok():
            self.toast("Agendado para %s às %s. O backend vai disparar na hora." % (date_str, time_str), "ok")
        else:
            self.toast("Salvo em scheduled_videos.json, mas o backend está OFFLINE — não vai disparar. Abra run_ui_premium.ps1.", "err")

    def cal_remove(self, schedule_id):
        remove_schedule(schedule_id)
        self.cal_refresh()
        self.toast("Agendamento removido.", "ok")

    # ----------------------------- diario existentes --------------------------
    def refresh_daily_list(self):
        for w in self.daily_list.winfo_children():
            w.destroy()
        topics = read_topics_daily()
        st = load_state_daily()
        done = set(st.get("done", {}).keys())
        failed = set(st.get("failed", {}).keys())
        pending = set(st.get("pending", {}).keys())
        for i, t in enumerate(topics[:12]):
            k = norm_daily(t)
            dot = T["ok"] if k in done else (T["err"] if k in failed else T["text3"])
            n = NavItem(self.daily_list, t, lambda t=t: None, right="",
                        dot=dot, bg=T["card"])
            n.pack(fill="x", pady=1)

    def daily_status(self):
        self._refresh_backend_lbl()
        try:
            out = subprocess.check_output([sys.executable, str(DAILY), "status"],
                                          stderr=subprocess.STDOUT, text=True, timeout=15)
        except subprocess.CalledProcessError as e:
            out = e.output or "Erro ao obter status"
        except Exception as e:
            out = "Erro: %s" % e
        self.daily_status_lbl.configure(text=out.strip()[:500])

    def _refresh_backend_lbl(self):
        if backend_ok():
            self.backend_lbl.configure(
                text="Backend :8765 online — agendamentos do calendário vão disparar na hora marcada.",
                fg=T["ok"])
        else:
            self.backend_lbl.configure(
                text="Backend :8765 OFFLINE — agendamentos do calendário NÃO vão disparar. Rode run_ui_premium.ps1.",
                fg=T["err"])

    def daily_run(self):
        self.start_daily(["run"])

    def daily_dry(self):
        self.start_daily(["run", "--dry-run"])

    def daily_no_upload(self):
        self.start_daily(["run", "--no-upload"])

    def daily_force(self):
        self.start_daily(["run", "--force"])

    def daily_unpause(self, requeue=False):
        cmd = ["run"] if not requeue else ["unpause", "--requeue-failed"]
        self.start_daily(cmd)

    def stop_agent(self):
        if self.running:
            self.toast("Há uma execução local em andamento. Use Parar primeiro.", "warn")
            return
        pids = self._agent_pids()
        if not pids:
            self.toast("Nenhum agente externo detectado.", "info")
            return
        n = 0
        for pid in pids:
            if self._kill_pid_tree(pid):
                n += 1
        self.toast("Agente externo: %d processo(s) encerrado(s)." % n, "warn")
        if self.page == "executivo":
            self.after(800, self.update_executivo)

    def start_daily(self, args):
        if self.running:
            self.toast("Já há uma execução em andamento.", "err")
            return
        cmd = [sys.executable, str(DAILY)] + args
        self.start(cmd, "daily", then_upload=False)

    # ------------------------------------------------------- atividade ---
    def _page_activity(self, page):
        M = P(32)
        tb = tk.Frame(page, bg=T["bg"])
        tb.pack(fill="x", padx=M, pady=(0, P(12)))
        Button(tb, "Status do projeto", self.run_status, "secondary", icon="📊").pack(side="left")
        Button(tb, "Copiar", self.copy_log, "secondary", icon="📋").pack(side="left",
                                                                         padx=P(8))
        Button(tb, "Limpar", self.clear_log, "ghost", icon="🗑").pack(side="left")
        c = Card(page, pad=6, radius=14, fill=T["log_bg"], outline=T["log_bg"], autoheight=False,
                 elevated=False)
        c.pack(fill="both", expand=True, padx=M, pady=(0, P(24)))
        wrap = tk.Frame(c.body, bg=T["log_bg"])
        wrap.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", style="Log.Vertical.TScrollbar")
        sb.pack(side="right", fill="y")
        self.log = tk.Text(wrap, wrap="word", state="disabled", relief="flat", bd=0, bg=T["log_bg"],
                           fg=T["log_fg"], font=fnt(9, False, True), padx=P(14), pady=P(12), height=5,
                           width=1, highlightthickness=0, yscrollcommand=sb.set,
                           selectbackground=T["accent"])
        sb.configure(command=self.log.yview)
        self.log.pack(side="left", fill="both", expand=True)
        for tag, col, bold in (("cmd", "#8E8E93", False), ("head", "#64D2FF", True), ("warn", "#FFD60A", False),
                               ("err", "#FF6961", True), ("ok", "#30D158", True), ("dim", "#8E8E93", False)):
            self.log.tag_configure(tag, foreground=col, font=fnt(9, bold, True))

    # --------------------------------------------------------- ajustes ---
    def _page_settings(self, root):
        M = P(32)
        c = Card(root, elevated=True)
        c.pack(fill="x", padx=M, pady=(P(4), P(16)))
        b = c.body
        lbl(b, "Ajustes da Interface", 14, True).pack(anchor="w")
        lbl(b, "Tema, zoom e outras preferências da UI.", 9, False, "text2").pack(anchor="w",
                                                                                pady=(P(2), P(14)))
        switch_row(b, "Tema escuro", "Ativa o tema escuro da interface", self.v_theme).pack(
            fill="x", pady=(0, P(16)))
        lbl(b, "Tema atual: %s" % self.v_theme.get(), 9, False, "text2").pack(anchor="w",
                                                                             pady=(0, P(16)))
        switch_row(b, "Salvar ajustes ao fechar", "Lembra duração, voz, YouTube e zoom",
                   tk.BooleanVar(value=True)).pack(fill="x", pady=(0, P(24)))

        c2 = Card(root, elevated=True)
        c2.pack(fill="x", padx=M, pady=(0, P(24)))
        b = c2.body
        lbl(b, "Atalhos de teclado", 13, True).pack(anchor="w", pady=(0, P(10)))
        shortcuts = [
            ("Ctrl + Enter", "Gerar vídeo"),
            ("Ctrl + =", "Aumentar zoom da interface"),
            ("Ctrl + -", "Diminuir zoom da interface"),
            ("Ctrl + 0", "Resetar zoom"),
        ]
        for k, v in shortcuts:
            row = tk.Frame(b, bg=T["card"])
            row.pack(fill="x", pady=P(4))
            lbl(row, k, 10, True, "accent", T["card"]).pack(side="left")
            lbl(row, "→ " + v, 10, False, "text2", T["card"]).pack(side="right")

    # -------------------------------------------------------- ligacoes ---
    def _wire(self):
        self.v_dur.trace_add("write", lambda *a: self.dur_lbl.configure(text=fmt_dur(self.v_dur.get())))
        self.v_mode.trace_add("write", lambda *a: self.refresh_chips())
        self.v_force.trace_add("write", lambda *a: self.update_summary())
        self.v_yt_mode.trace_add("write", lambda *a: self._yt_help())
        self.v_yt_priv.trace_add("write", lambda *a: self._yt_help())
        self.v_yt_video.trace_add("write", lambda *a: self.update_yt_info())
        for v in (self.v_voice, self.v_rate, self.v_pitch):
            v.trace_add("write", lambda *a: self._voice_summary())
        self._yt_help()
        self._voice_summary()
        self.on_prompt_change()

    def _yt_help(self):
        self.yt_mode_help.configure(text=YT_MODE_HELP.get(self.v_yt_mode.get(), ""))
        self.yt_priv_help.configure(text=PRIV_HELP.get(self.v_yt_priv.get(), ""))

    def _voice_summary(self):
        self.voice_box.set_summary("%s · %s · %s" % (self.v_voice.get(), self.v_rate.get(),
                                                     self.v_pitch.get()))

    # ---------------------------------------------------------- paginas ---
    def show_page(self, key):
        self.page = key
        for k, p in self.pages.items():
            p.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        for k, n in self.nav.items():
            n.set_selected(k == key)
        if key == "activity":
            self.nav["activity"].badge = False
            self.nav["activity"]._draw()
        t, s = PAGE_TEXT[key]
        self.h_title.configure(text=t)
        self.h_sub.configure(text=s)
        if key == "publish":
            self.update_yt_info()
        elif key == "daily":
            self.daily_status()
            self.refresh_daily_list()
        elif key == "executivo":
            self.update_executivo()

    def _wheel(self, e, direction=None):
        if self.page not in ("create", "publish", "daily", "executivo"):
            return
        sf = self.pages[self.page]
        x, y = sf.winfo_rootx(), sf.winfo_rooty()
        if not (x <= e.x_root <= x + sf.winfo_width() and y <= e.y_root <= y + sf.winfo_height()):
            return
        if direction is None:
            d = e.delta
            direction = -int(d / 120) if abs(d) >= 120 else (-1 if d > 0 else 1)
        sf.wheel(direction * 2)

    def toast(self, text, kind="info"):
        if self._toast is not None:
            try:
                self._toast.destroy()
            except tk.TclError:
                pass
        bg, fg = (T["err"], "#FFFFFF") if kind == "err" else (T["toast"], T["on_toast"])
        t = tk.Label(self.main, text=text, bg=bg, fg=fg, font=fnt(10, True), padx=P(20),
                     pady=P(10))
        t.place(relx=0.5, rely=1.0, y=-P(100), anchor="s")
        self._toast = t

        def gone():
            try:
                t.destroy()
            except tk.TclError:
                pass
        self.after(3600, gone)

    # ----------------------------------------------------------- prompt ---
    def _p_in(self):
        if self.ph:
            self.prompt.delete("1.0", "end")
            self.prompt.configure(fg=T["text"])
            self.ph = False

    def _p_out(self):
        if not self.prompt.get("1.0", "end").strip():
            self.prompt.delete("1.0", "end")
            self.prompt.insert("1.0", PLACEHOLDER)
            self.prompt.configure(fg=T["text3"])
            self.ph = True

    def get_prompt(self):
        return "" if self.ph else self.prompt.get("1.0", "end").strip()

    def set_prompt(self, text):
        self.ph = False
        self.prompt.configure(fg=T["text"])
        self.prompt.delete("1.0", "end")
        self.prompt.insert("1.0", text)
        self._p_out()
        self.on_prompt_change(keep_override=True)

    def current_slug(self):
        return self.slug_override or slugify(self.get_prompt())

    def on_prompt_change(self, e=None, keep_override=False):
        if not keep_override and self.slug_override and self.get_prompt() != self._loaded_prompt:
            self.slug_override = None
        self.slug_lbl.configure(text=self.current_slug() or "—")
        if self._chips_job:
            self.after_cancel(self._chips_job)
        self._chips_job = self.after(300, self._slug_changed)

    def _slug_changed(self):
        self.refresh_chips()
        self.refresh_projects()
        self.update_yt_info()

    def load_project(self, slug):
        prompt = load_state(slug).get("prompt") or slug.replace("-", " ")
        self.set_prompt(prompt)
        self.slug_override, self._loaded_prompt = slug, self.get_prompt()
        self.v_yt_video.set("")
        self.slug_lbl.configure(text=slug)
        self.show_page("create")
        self._slug_changed()

    # ----------------------------------------------------------- etapas ---
    def chip_click(self, key):
        if self.running:
            return
        mode, i = self.v_mode.get(), PHASE_KEYS.index(key)
        if mode == "from":
            self.from_idx = i
        elif mode in ("only", "skip"):
            s = self.only_set if mode == "only" else self.skip_set
            s.symmetric_difference_update({key})
        self.refresh_chips()

    def refresh_chips(self):
        mode = self.v_mode.get()
        slug = self.current_slug()
        done = done_phases(slug)
        running = None
        if self.running and self.task == "pipeline" and self.plan:
            pend = [k for k in PHASE_KEYS if k in self.plan and k not in done]
            running = pend[0] if pend else None
        for i, (k, chip) in enumerate(self.chips):
            if self.running and self.task == "pipeline" and self.plan is not None:
                run = k in self.plan
            elif mode == "auto":
                run = True
            elif mode == "from":
                run = i >= self.from_idx
            elif mode == "only":
                run = k in self.only_set
            else:
                run = k not in self.skip_set
            chip.set_state(run, "running" if k == running else "done" if k in done else "",
                           mode != "auto" and not self.running, mode == "skip" and not run)
        self.update_summary()

    def update_summary(self):
        mode = self.v_mode.get()
        if mode == "auto":
            t = "Retoma do ponto em que parou (checkpoints) e segue até o render."
        elif mode == "from":
            t = "Executa de %s até Render · %d etapas. Toque numa etapa para mudar o início." % (
                PHASE_NAME[PHASE_KEYS[self.from_idx]], len(PHASES) - self.from_idx)
        elif mode == "only":
            sel = [PHASE_NAME[k] for k in PHASE_KEYS if k in self.only_set]
            t = "Executa somente: " + " → ".join(sel) if sel else "Toque nas etapas que deseja executar."
        else:
            sel = [PHASE_NAME[k] for k in PHASE_KEYS if k in self.skip_set]
            t = "Executa tudo, exceto: " + ", ".join(sel) if sel else "Toque nas etapas que deseja pular."
        if self.v_force.get():
            t += "  Checkpoints serão ignorados."
        self.summary.configure(text=t)

    def phase_args(self):
        mode = self.v_mode.get()
        if mode == "from":
            return ["--from", PHASE_KEYS[self.from_idx]]
        if mode == "only":
            return ["--only", ",".join(k for k in PHASE_KEYS if k in self.only_set)]
        if mode == "skip" and self.skip_set:
            return ["--skip", ",".join(k for k in PHASE_KEYS if k in self.skip_set)]
        return []

    # ---------------------------------------------------------- projetos ---
    def refresh_projects(self):
        for w in self.proj_box.winfo_children():
            w.destroy()
        items = list_projects()[:7]
        if not items:
            lbl(self.proj_box, "Nenhum projeto ainda", 9, False, "text3", T["sidebar"]).pack(
                anchor="w", padx=P(12), pady=P(4))
            return
        cur = self.current_slug()
        for it in items:
            n = NavItem(self.proj_box, it["slug"], lambda s=it["slug"]: self.load_project(s),
                        right="%d/%d" % (it["done"], len(PHASES)),
                        dot=T["ok"] if it["video"] else T["text3"])
            n.set_selected(it["slug"] == cur)
            n.pack(fill="x", pady=1)

    # ---------------------------------------------------------- execucao ---
    def run_pipeline(self, sub):
        if self.running:
            return
        prompt = self.get_prompt()
        if sub == "full" and not prompt:
            self.toast("Descreva o vídeo antes de gerar.", "err")
            self.show_page("create")
            self.prompt.focus_set()
            return
        slug = self.current_slug()
        if sub == "resume":
            if not slug or not (ROOT / "projects" / slug / "project.json").is_file():
                self.toast("Esse projeto ainda não existe. Use Gerar vídeo.", "err")
                return
        if self.v_mode.get() == "only" and not self.only_set:
            self.toast("Selecione ao menos uma etapa em “Somente”.", "err")
            return
        cmd = [sys.executable, str(PIPELINE), sub]
        if sub == "full":
            cmd += ["--prompt", prompt]
            if self.slug_override:
                cmd += ["--slug", self.slug_override]
        else:
            cmd += ["--slug", slug]
        cmd += self.phase_args()
        if self.v_force.get():
            cmd.append("--force")
        if self.v_nopar.get():
            cmd.append("--no-parallel")
        if self.v_skipchk.get():
            cmd.append("--skip-check")
        cmd += ["--voice", self.v_voice.get(), "--rate", self.v_rate.get(), "--pitch",
                self.v_pitch.get(), "--wait", self.v_wait.get()]
        cmd += ["--narration-provider", self.v_narr_provider.get()]
        if self.v_style.get().strip():
            cmd += ["--style", self.v_style.get().strip()]
        cmd += ["--duration", str(self.v_dur.get())]
        self.start(cmd, "pipeline", then_upload=self.v_yt_mode.get() in ("auto", "ask"))

    def run_status(self):
        if self.running:
            return
        slug = self.current_slug()
        if not slug:
            self.toast("Descreva o vídeo ou escolha um projeto.", "err")
            return
        self.start([sys.executable, str(PIPELINE), "status", "--slug", slug], "status")

    def start(self, cmd, task, clear=True, then_upload=False):
        self.running, self.task, self.plan, self.up_pct = True, task, None, None
        self.stopping, self.then_upload, self.run_started = False, then_upload, time.time()
        self._set_extra(None)
        for b in (self.btn_run, self.btn_resume, self.btn_upload):
            b.set_enabled(False)
        if task != "status":
            self.btn_stop.pack(side="left", padx=(0, P(8)), before=self.btn_resume)
        if clear:
            self.clear_log()
        self.log_line("$ " + _sh(cmd), "cmd")
        self.pill.set("run", {"pipeline": "Gerando vídeo", "upload": "Enviando",
                              "status": "Consultando", "daily": "Executando diário"}[task])
        self._update_status()
        self.refresh_chips()
        threading.Thread(target=self._reader, args=(cmd,), daemon=True).start()

    def _reader(self, cmd):
        try:
            env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
            kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1,
                                         cwd=str(ROOT), env=env, **kw)
            for line in self.proc.stdout:
                self.q.put(("line", line.rstrip("\r\n")))
            self.proc.wait()
            self.q.put(("done", self.proc.returncode))
        except Exception as e:
            self.q.put(("line", "ERRO: %s" % e))
            self.q.put(("done", -1))

    def _drain(self):
        try:
            for _ in range(300):
                kind, val = self.q.get_nowait()
                if kind == "line":
                    self._on_line(val)
                else:
                    self._on_done(val)
        except queue.Empty:
            pass
        self.after(60, self._drain)

    def _on_line(self, line):
        low = line.lower()
        if line.startswith("OK:") or "concluido" in low or "upload 100%" in low or "publicado" in low:
            tag = "ok"
        elif line.startswith("== "):
            tag = "head"
        elif line.startswith("AVISO") or "caducado" in low:
            tag = "warn"
        elif line.startswith("ERRO") or "traceback" in low or "error" in low[:12]:
            tag = "err"
        else:
            tag = ""
        self.log_line(line, tag)
        m = re.match(r"== Planejado: (\[.*\])", line)
        if m:
            try:
                self.plan = list(ast.literal_eval(m.group(1)))
            except Exception:
                pass
            self.refresh_chips()
        elif "Nada a fazer" in line:
            self.plan = []
        m = re.search(r"UPLOAD (\d+)%", line)
        if m:
            self.up_pct = int(m.group(1))
        m = re.match(r"OK: (https://youtu\.be/\S+)", line)
        if m:
            self._link = m.group(1)
        self._update_status()

    def _update_status(self):
        if not self.running:
            return
        if self.task == "upload":
            if self.up_pct is None:
                self.st_text.configure(text="Preparando envio…")
                self.progress.set(None)
            else:
                self.st_text.configure(text="Enviando ao YouTube · %d%%" % self.up_pct)
                self.progress.set(self.up_pct / 100.0)
        elif self.task == "pipeline":
            if self.plan is None:
                self.st_text.configure(text="Iniciando…")
                self.progress.set(None)
            elif not self.plan:
                self.st_text.configure(text="Nada a fazer: tudo já está concluído")
                self.progress.set(1.0)
            else:
                done = done_phases(self.current_slug()) & set(self.plan)
                n = len(self.plan)
                cur = next((k for k in PHASE_KEYS if k in self.plan and k not in done), None)
                self.st_text.configure(text="%s · etapa %d de %d" % (
                    PHASE_NAME[cur] if cur else "Finalizando", min(len(done) + 1, n), n))
                self.progress.set(len(done) / float(n))
        elif self.task == "daily":
            self.st_text.configure(text="Executando diário…")
            self.progress.set(None)
        else:
            self.st_text.configure(text="Consultando status…")
            self.progress.set(None)

    def _on_done(self, code):
        task, stopped = self.task, self.stopping
        self.running, self.proc = False, None
        ok = code == 0 and not stopped
        self.log_line("— fim (código %s) —" % code, "ok" if ok else "err" if not stopped else "dim")
        self.pill.set("idle" if stopped else "ok" if ok else "err",
                      "Interrompido" if stopped else "Concluído" if ok else "Falhou")
        label = {"pipeline": "Vídeo gerado", "upload": "Enviado ao YouTube",
                 "status": "Status consultado", "daily": "Diário concluído"}[task]
        self.st_text.configure(text=("Interrompido" if stopped else label if ok else
                                     "Falhou · veja Atividade"))
        self.progress.set(1.0 if ok and task != "status" else 0.0)
        self.btn_stop.pack_forget()
        for b in (self.btn_run, self.btn_resume, self.btn_upload):
            b.set_enabled(True)
        if self.page != "activity":
            self.nav["activity"].badge = True
            self.nav["activity"]._draw()
        self.refresh_chips()
        self.refresh_projects()
        self.update_yt_info()
        if self.page == "daily":
            self.refresh_daily_list()
        if ok and task == "pipeline":
            v = self.video_path()
            if v.is_file():
                self._set_extra("Abrir vídeo", lambda: open_path(v))
            if self.then_upload:
                self.then_upload = False
                self.after(0, self._after_pipeline_upload)
        elif ok and task == "upload" and getattr(self, "_link", None):
            link = self._link
            self._set_extra("Abrir no YouTube", lambda: webbrowser.open(link))
            self.toast("Vídeo enviado ao YouTube")
        elif not ok and not stopped and task != "status":
            self.toast("A execução falhou. Veja os detalhes em Atividade.", "err")
            self.show_page("activity")

    def _set_extra(self, text, fn=None):
        self.btn_extra.pack_forget()
        if text:
            self.btn_extra.set_text(text)
            self.btn_extra.cmd = fn
            self.btn_extra.pack(side="left", padx=(0, P(8)), before=self.btn_resume)

    def stop_run(self):
        if self.proc and self.proc.poll() is None:
            if messagebox.askyesno("Parar", "Encerrar o processo em execução?"):
                self.stopping = True
                if not self._kill_pid_tree(self.proc.pid):
                    self.proc.terminate()

    def stop_all(self):
        if not messagebox.askyesno("Parar tudo", "Encerrar o pipeline local e agentes externos?"):
            return
        self.stopping = True
        killed = 0
        if self.proc and self.proc.poll() is None:
            if self._kill_pid_tree(self.proc.pid):
                killed += 1
        for pid in self._agent_pids():
            if self._kill_pid_tree(pid):
                killed += 1
        self.toast("Parada enviada: %d processo(s)." % killed, "warn")

    def _poll(self):
        if self.running and self.task == "pipeline":
            self.refresh_chips()
            self._update_status()
        self.after(1200, self._poll)

    def _pulse(self):
        PULSE[0] = not PULSE[0]
        if self.running:
            self.pill.draw()
            for _, chip in self.chips:
                if chip.status == "running":
                    chip.draw()
        self.after(500, self._pulse)

    # -------------------------------------------------------------- log ---
    def log_line(self, text, tag=""):
        at_end = self.log.yview()[1] > 0.98
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or ())
        self.log.configure(state="disabled")
        if at_end:
            self.log.see("end")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log.get("1.0", "end"))
        self.toast("Saída copiada")

    # ---------------------------------------------------------- youtube ---
    def pick_video(self):
        p = filedialog.askopenfilename(title="Escolher vídeo",
                                       filetypes=[("Vídeo MP4", "*.mp4"), ("Todos", "*.*")],
                                       initialdir=str(ROOT / "projects"))
        if p:
            self.v_yt_video.set(p)

    def pick_thumb(self):
        p = filedialog.askopenfilename(title="Escolher thumbnail",
                                       filetypes=[("Imagem", "*.jpg *.jpeg *.png"), ("Todos", "*.*")])
        if p:
            self.v_yt_thumb.set(p)

    def pick_secret(self):
        p = filedialog.askopenfilename(title="client_secret.json",
                                       filetypes=[("JSON", "*.json"), ("Todos", "*.*")])
        if p:
            self.v_yt_secret.set(p)

    def video_path(self):
        p = self.v_yt_video.get().strip()
        if p:
            return Path(p)
        slug = self.current_slug() or "projeto"
        return ROOT / "projects" / slug / "output" / ("%s.mp4" % slug)

    def update_yt_info(self):
        if not hasattr(self, "yt_info"):
            return
        v = self.video_path()
        if v.is_file():
            self.yt_info.configure(text="✓  %s · %.1f MB" % (v.name, v.stat().st_size / 1e6),
                                   fg=T["ok"])
        else:
            self.yt_info.configure(text="Vídeo ainda não encontrado: %s" % v, fg=T["warn"])

    def build_upload_cmd(self):
        video = self.video_path()
        if not video.is_file():
            return None, video
        prompt = self.get_prompt()
        title = self.v_yt_title.get().strip() or prompt.split("\n")[0][:100] or video.stem
        desc = self.yt_desc.get("1.0", "end").strip() or prompt
        cmd = [sys.executable, str(UPLOADER), "--video", str(video), "--title=" + title,
               "--description=" + desc,
               "--tags=" + self.v_yt_tags.get().strip(),
               "--category=" + (self.v_yt_cat.get().strip() or "22"),
               "--privacy=" + self.v_yt_priv.get(),
               "--client-secret=" + self.v_yt_secret.get().strip()]
        if self.v_yt_kids.get():
            cmd.append("--made-for-kids")
        if self.v_yt_when.get().strip():
            cmd.append("--publish-at=" + self.v_yt_when.get().strip())
        if self.v_yt_thumb.get().strip():
            cmd.append("--thumbnail=" + self.v_yt_thumb.get().strip())
        return cmd, video

    def run_upload(self, clear=True):
        if self.running:
            return
        cmd, video = self.build_upload_cmd()
        if cmd is None:
            self.toast("Vídeo não encontrado. Gere o vídeo ou escolha um arquivo.", "err")
            return
        self._link = None
        self.start(cmd, "upload", clear=clear)

    def _after_pipeline_upload(self):
        video = self.video_path()
        if not video.is_file() or video.stat().st_mtime < self.run_started - 2:
            self.log_line("== YouTube: nenhum vídeo novo nesta execução; envio ignorado.", "head")
            return
        if self.v_yt_mode.get() == "ask" and not messagebox.askyesno(
                "YouTube", "Vídeo pronto:\n%s\n\nEnviar para o YouTube agora?" % video):
            self.log_line("== YouTube: envio adiado (use o botão Enviar quando quiser).", "head")
            return
        self.run_upload(clear=False)

    # ------------------------------------------------------- configuracao ---
    def load_settings(self):
        try:
            data = json.loads(SETTINGS.read_text(encoding="utf-8"))
            for k, var in self.saved.items():
                if k in data:
                    var.set(data[k])
        except Exception:
            pass

    def save_settings(self):
        try:
            SETTINGS.write_text(json.dumps({k: v.get() for k, v in self.saved.items()},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def on_close(self):
        if self.running and self.proc and self.proc.poll() is None:
            if not messagebox.askyesno("Sair", "Há uma execução em andamento. Encerrar e sair?"):
                return
            self.proc.terminate()
        self.save_settings()
        self.destroy()


# -------------------------------------------------------------- diario utils ---
def read_topics_daily():
    out = []
    if TOPICS.is_file():
        for line in TOPICS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def load_state_daily():
    st = {"done": {}, "failed": {}, "pending": {}, "attempts": {}, "last_run_date": None,
          "consecutive_failed": 0, "paused": False, "pause_reason": ""}
    try:
        st.update(json.loads((ROOT / "daily_state.json").read_text(encoding="utf-8")))
    except Exception:
        pass
    return st


def norm_daily(text):
    return re.sub(r"\s+", " ", text.strip()).casefold()


# --------------------------------------------------------------------- main ---
def enable_dpi():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser(description="Videomaker - UI Premium do pipeline v3")
    ap.add_argument("-p", "--prompt", default=None, help="Preenche o campo de prompt na abertura")
    ap.add_argument("--theme", default="auto", choices=["auto", "light", "dark"])
    args = ap.parse_args()
    enable_dpi()
    app = App(theme=args.theme, prompt=args.prompt)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
