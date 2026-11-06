# -*- coding: utf-8 -*-
"""
UI local (tkinter, sem dependencia externa) para o pipeline de video v3.

Usage:
  python scripts/pipeline_ui.py [-p "<prompt>"]

Features:
  - Prompt -> slug (derive automaticamente, visualizavel)
  - Selecao de fases: "A partir de..." (--from) ou "Somente" (--only) ou "Pular" (--skip)
  - Opcao reprocessar tudo ignorando checkpoints (--force)
  - Paralelismo desativado (--no-parallel)
  - Duracao alvo do video (target_duration_s)
  - Voz/rate/pitch/estilo
  - Botoes: Rodar (full), Retomar (resume), Status, Parar, Sair
"""
import argparse
import re
import unicodedata
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIPELINE = HERE / "pipeline.py"


def slugify(text, max_len=40):
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    norm = re.sub(r"[^a-z0-9\s-]", "", norm.lower())
    norm = re.sub(r"[\s_-]+", "-", norm).strip("-")
    return norm[:max_len].rstrip("-")


PHASES = [
    ("script", "Roteiro (IA web Gemini)"),
    ("scenes", "Cenas + HTML (IA)"),
    ("images", "Imagens (IA web Gemini)"),
    ("music", "Musica (IA web / procedural)"),
    ("narration", "Narracao (Edge-TTS local)"),
    ("timeline", "Linha do tempo"),
    ("mix", "Mixagem de audio"),
    ("compose", "Composicao HyperFrames"),
    ("preprocess", "Pre-processamento de imagens"),
    ("render", "Render final (MP4)"),
]


class PipelineUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Videomaker - Pipeline de Video v3")
        self.geometry("1000x820")
        self.minsize(820, 680)

        self.proc = None

        # --- Prompt ---
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(top, text="Prompt do video:", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.prompt = tk.Text(self, height=3, wrap="word")
        self.prompt.pack(fill="x", padx=10, pady=4)
        self.prompt.bind("<KeyRelease>", self.on_prompt_change)

        slug_row = ttk.Frame(self)
        slug_row.pack(fill="x", padx=10, pady=(0, 4))
        ttk.Label(slug_row, text="Projeto (slug):").pack(side="left")
        self.slug_var = tk.StringVar()
        ttk.Label(slug_row, textvariable=self.slug_var, font=("Consolas", 10),
                  foreground="#555").pack(side="left", padx=8)

        # --- Duracao alvo ---
        dur_row = ttk.Frame(self)
        dur_row.pack(fill="x", padx=10, pady=(0, 4))
        ttk.Label(dur_row, text="Duracao alvo (s):").pack(side="left")
        self.duration_s = tk.StringVar(value="590")
        ttk.Entry(dur_row, textvariable=self.duration_s, width=8).pack(side="left", padx=8)
        ttk.Label(dur_row, text="(aprox. 10 min = 600s)", font=("Segoe UI", 9), foreground="#777").pack(side="left", padx=4)

        # --- Fases ---
        ttk.Label(self, text="Fases:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self.vars = {}
        grid = ttk.Frame(self)
        grid.pack(fill="x", padx=10, pady=4)
        for i, (key, label) in enumerate(PHASES):
            var = tk.BooleanVar(value=True)
            self.vars[key] = var
            cb = ttk.Checkbutton(grid, text=label, variable=var, command=self.on_phase_change)
            cb.grid(row=i // 2, column=i % 2, padx=4, pady=2, sticky="w")

        # --- Opcoes ---
        opts = ttk.LabelFrame(self, text="Opcoes")
        opts.pack(fill="x", padx=10, pady=6)

        # Linha 0: Force + No-parallel
        self.var_force = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Force re-fazer (ignora checkpoints)", variable=self.var_force).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=6, pady=3)

        self.var_no_parallel = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Sem paralelismo (--no-parallel)", variable=self.var_no_parallel).grid(
            row=0, column=3, columnspan=3, sticky="w", padx=6, pady=3)

        # Linha 1: Modo de execucao
        ttk.Label(opts, text="Modo:").grid(row=1, column=0, sticky="e", padx=8, pady=3)
        self.mode_var = tk.StringVar(value="auto")
        mode_combo = ttk.Combobox(opts, textvariable=self.mode_var, width=14, state="readonly",
                                  values=["auto", "from", "only", "skip"])
        mode_combo.grid(row=1, column=1, padx=4, pady=3)
        ttk.Label(opts, text="(auto detecta: prefixo=from, sufixo=only, meio=skip)").grid(
            row=1, column=2, columnspan=4, sticky="w", padx=4)

        # Linha 2: from_phase (quando modo=from)
        ttk.Label(opts, text="Fase inicial (--from):").grid(row=2, column=0, sticky="e", padx=8, pady=3)
        self.from_phase = tk.StringVar(value="auto")
        from_combo = ttk.Combobox(opts, textvariable=self.from_phase, width=14, state="readonly",
                                  values=["auto"] + [k for k, _ in PHASES])
        from_combo.grid(row=2, column=1, padx=4, pady=3)

        # Linha 3: only_phases (quando modo=only)
        ttk.Label(opts, text="Apenas fases (--only):").grid(row=3, column=0, sticky="e", padx=8, pady=3)
        self.only_phases = tk.StringVar(value="")
        ttk.Entry(opts, textvariable=self.only_phases, width=40).grid(row=3, column=1, columnspan=4, padx=4, pady=3, sticky="ew")
        ttk.Label(opts, text="(ex: mix,compose)").grid(row=3, column=5, sticky="w", padx=4)

        # Linha 4: skip_phases (quando modo=skip)
        ttk.Label(opts, text="Pular fases (--skip):").grid(row=4, column=0, sticky="e", padx=8, pady=3)
        self.skip_phases = tk.StringVar(value="")
        ttk.Entry(opts, textvariable=self.skip_phases, width=40).grid(row=4, column=1, columnspan=4, padx=4, pady=3, sticky="ew")
        ttk.Label(opts, text="(ex: script,scenes,images)").grid(row=4, column=5, sticky="w", padx=4)

        # Linha 5: Voz / Vel / Tom / Espera
        ttk.Label(opts, text="Voz:").grid(row=5, column=0, sticky="e", padx=8, pady=3)
        self.voice = tk.StringVar(value="pt-BR-ThalitaNeural")
        ttk.Entry(opts, textvariable=self.voice, width=22).grid(row=5, column=1, padx=4, columnspan=2)
        ttk.Label(opts, text="Vel.:").grid(row=5, column=3, sticky="e")
        self.rate = tk.StringVar(value="+12%")
        ttk.Entry(opts, textvariable=self.rate, width=7).grid(row=5, column=4)
        ttk.Label(opts, text="Tom:").grid(row=5, column=5, sticky="e")
        self.pitch = tk.StringVar(value="+8Hz")
        ttk.Entry(opts, textvariable=self.pitch, width=7).grid(row=5, column=6)
        ttk.Label(opts, text="Espera max (IA web, s):").grid(row=5, column=7, sticky="e", padx=6)
        self.wait_s = tk.StringVar(value="240")
        ttk.Entry(opts, textvariable=self.wait_s, width=7).grid(row=5, column=8)

        opts.columnconfigure(1, weight=1)

        # --- Botoes ---
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=6)
        self.btn_run = ttk.Button(btns, text="▶ Rodar (full)", command=lambda: self.run_pipeline("full"))
        self.btn_run.pack(side="left")
        self.btn_resume = ttk.Button(btns, text="⏭ Retomar (resume)", command=lambda: self.run_pipeline("resume"))
        self.btn_resume.pack(side="left", padx=6)
        ttk.Button(btns, text="✔ Status", command=self.run_status).pack(side="left", padx=6)
        ttk.Button(btns, text="Limpar saida", command=self.clear_log).pack(side="left", padx=6)
        ttk.Button(btns, text="Parar", command=self.stop_run).pack(side="left", padx=6)
        ttk.Button(btns, text="Sair", command=self.destroy).pack(side="right")

        # --- Log ---
        ttk.Label(self, text="Saida:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        self.log = tk.Text(self, wrap="word", state="disabled", font=("Consolas", 10))
        self.log.pack(fill="both", expand=True, padx=10, pady=5)

        self.status = ttk.Label(self, text="Pronto", relief="sunken", anchor="w")
        self.status.pack(side="bottom", fill="x")

        self.on_prompt_change()

    def current_slug(self):
        prompt = self.prompt.get("1.0", "end").strip()
        return slugify(prompt)

    def selected_phases(self):
        return [key for key, _ in PHASES if self.vars[key].get()]

    def run_pipeline(self, subcmd):
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Aviso", "Digite um prompt.")
            return

        selected = self.selected_phases()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione pelo menos uma fase.")
            return

        # Determina argumentos de fase
        mode = self.mode_var.get()
        phase_args = []
        if mode == "from":
            phase_args = ["--from", self.from_phase.get()]
        elif mode == "only":
            val = self.only_phases.get().strip()
            if val:
                phase_args = ["--only", val]
            else:
                messagebox.showwarning("Aviso", "Modo 'only' requer lista de fases.")
                return
        elif mode == "skip":
            val = self.skip_phases.get().strip()
            if val:
                phase_args = ["--skip", val]
            else:
                messagebox.showwarning("Aviso", "Modo 'skip' requer lista de fases.")
                return
        # mode == "auto": usa logica antiga baseada em selecao
        else:
            order_all = [k for k, _ in PHASES]
            sel_set = set(selected)
            if len(selected) == len(order_all):
                phase_args = []
            elif selected == order_all[:len(selected)]:
                phase_args = ["--from", selected[0]]
            elif selected == order_all[-len(selected):]:
                phase_args = ["--only", ",".join(selected)]
            else:
                phase_args = ["--skip", ",".join(k for k in order_all if k not in sel_set)]

        cmd = [sys.executable, str(PIPELINE), subcmd]
        if subcmd == "full":
            cmd += ["--prompt", prompt]
        else:  # resume
            cmd += ["--slug", self.current_slug()]
        cmd += phase_args
        if self.var_force.get():
            cmd += ["--force"]
        if self.var_no_parallel.get():
            cmd += ["--no-parallel"]
        cmd += ["--voice", str(self.voice.get())]
        cmd += ["--rate", str(self.rate.get())]
        cmd += ["--pitch", str(self.pitch.get())]
        cmd += ["--wait", str(self.wait_s.get())]
        dur = self.duration_s.get().strip()
        if dur:
            cmd += ["--duration", dur]
        self._execute(cmd, desc=f"Rodando pipeline ({subcmd})")

    def run_status(self):
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Aviso", "Digite um prompt.")
            return
        slug = self.current_slug()
        cmd = [sys.executable, str(PIPELINE), "status", "--slug", slug]
        self._execute(cmd, desc="Status")

    def stop_run(self):
        if self.proc and self.proc.poll() is None:
            if messagebox.askyesno("Parar", "Encerrar o processo do pipeline?"):
                self.proc.terminate()

    def _execute(self, cmd, desc=""):
        self.btn_run.configure(state="disabled")
        self.btn_resume.configure(state="disabled")
        self.status.configure(text=desc + "...")
        self.clear_log()
        self.log_msg("== CMD: %s" % _sh(cmd))
        threading.Thread(target=self._wait_proc, args=(cmd,), daemon=True).start()

    def _wait_proc(self, cmd):
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True,
                                         bufsize=1, cwd=str(HERE.parent))
            for line in iter(self.proc.stdout.readline, ""):
                self.log_msg(line.rstrip())
            self.proc.wait()
            self.finished(self.proc.returncode)
        except Exception as e:
            self.log_msg("ERRO: %s" % str(e))
            self.finished(-1)

    def finished(self, code):
        self.log_msg("== EXIT: %s" % code)
        self.status.configure(
            text=("Falhou (codigo %s)" % code) if code else "OK (exit 0)")
        self.log_msg("== %s" % ("OK: CONCLUIDO" if not code else "ERRO."))
        self.btn_run.configure(state="normal")
        self.btn_resume.configure(state="normal")

    def log_msg(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def on_prompt_change(self, *a):
        self.slug_var.set(self.current_slug())

    def on_phase_change(self):
        sel = [k for k, _ in PHASES if self.vars[k].get()]
        self.status.configure(
            text="Fases: %d (%s)" % (len(sel), ", ".join(sel) if sel else "-"))


def _sh(cmd):
    return " ".join('"%s"' % c if not c[0].isalnum() and c[0] != "-" else c
                    for c in cmd)


def main():
    ap = argparse.ArgumentParser(description="UI do pipeline v3 (tkinter)")
    ap.add_argument("-p", "--prompt", default=None,
                    help="Preenche o campo de prompt na abertura")
    args = ap.parse_args()
    app = PipelineUI()
    if args.prompt:
        app.prompt.delete("1.0", "end")
        app.prompt.insert("1.0", args.prompt)
        app.on_prompt_change()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())