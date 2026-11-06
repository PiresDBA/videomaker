# -*- coding: utf-8 -*-
"""
Executor diario do Videomaker: 1 assunto da fila -> 1 video -> upload no YouTube.

Arquivos (todos em scripts/, exceto estado e logs):
  topics.txt            fila de assuntos (1 por linha; acrescente novos no FINAL)
  prompt_template.txt   modelo do prompt; {topic} e {minutes} sao preenchidos
  daily_config.json     horario, privacidade, tags, tentativas... (criado na 1a execucao)
  ../daily_state.json   o que ja foi feito / pendente / falhou
  ../logs/daily-AAAA-MM-DD.log

Comandos:
  python scripts/daily_runner.py status            situacao da fila e previsao de termino
  python scripts/daily_runner.py run               gera + envia o proximo episodio (1x por dia)
  python scripts/daily_runner.py run --dry-run     mostra o que faria, sem rodar nada
  python scripts/daily_runner.py run --no-upload   gera o video mas nao envia
  python scripts/daily_runner.py run --force       roda mesmo que hoje ja tenha rodado
  python scripts/daily_runner.py loop              fica rodando e dispara todo dia no horario
  python scripts/daily_runner.py install           cria a tarefa diaria no Agendador do Windows
  python scripts/daily_runner.py uninstall         remove a tarefa
  python scripts/daily_runner.py unpause           libera a fila depois de uma pausa de seguranca
  python scripts/daily_runner.py unpause --requeue-failed   idem + recoloca os assuntos que falharam
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PIPELINE = HERE / "pipeline.py"
UPLOADER = HERE / "youtube_upload.py"
TOPICS = HERE / "topics.txt"
TEMPLATE = HERE / "prompt_template.txt"
CONFIG = HERE / "daily_config.json"
STATE = ROOT / "daily_state.json"
LOCK = ROOT / ".daily.lock"

sys.path.insert(0, str(HERE))
import prompt_gen
LOGDIR = ROOT / "logs"
TASK_NAME = "Videomaker Daily"

DEFAULT_CONFIG = {
    "time": "09:00",
    "duration_s": 590,
    "upload": True,
    "privacy": "private",
    "made_for_kids": False,
    "category": "24",
    "tags": "cachorro,pet,animação,desenho animado,vídeo infantil,frida e luna",
    "title_suffix": "",
    "description_template": "{topic}\n\nUm episódio novo com a Frida e a Luna!\nInscreva-se para ver um vídeo novo todos os dias.",
    "client_secret": str(HERE / "client_secret.json"),
    "pipeline_args": [],
    "max_attempts": 3,
    "retry_wait_min": 10,
    "max_hours": 5,
    "pause_after_failed_topics": 2,
}
DEFAULT_TEMPLATE = (HERE / "prompt_template.txt").read_text(encoding="utf-8") if TEMPLATE.is_file() else \
    "Tema do episódio: {topic}\n\nEscreva o ROTEIRO (apenas texto) de um episódio animado de cerca de {minutes} minutos. Você não cria vídeo nem imagem nesta etapa.\n"


# ------------------------------------------------------------- utilidades ---
def slugify(text, max_len=40):
    s = unicodedata.normalize("NFKD", text.lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:max_len].strip("-")


def norm(text):
    return re.sub(r"\s+", " ", text.strip()).casefold()


def make_slug(topic):
    base = slugify(topic, 36) or "episodio"
    return "%s-%s" % (base, hashlib.md5(norm(topic).encode("utf-8")).hexdigest()[:4])


class Log:
    def __init__(self):
        LOGDIR.mkdir(exist_ok=True)
        self.path = LOGDIR / ("daily-%s.log" % datetime.now().strftime("%Y-%m-%d"))

    def raw(self, line):
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        if sys.stdout:
            try:
                print(line, flush=True)
            except Exception:
                pass

    def __call__(self, msg=""):
        self.raw("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_config():
    if not CONFIG.is_file():
        save_json(CONFIG, DEFAULT_CONFIG)
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(load_json(CONFIG, {}))
    if not TEMPLATE.is_file():
        TEMPLATE.write_text(DEFAULT_TEMPLATE, encoding="utf-8")
    return cfg


def load_state():
    st = {"done": {}, "failed": {}, "pending": {}, "attempts": {}, "last_run_date": None,
          "consecutive_failed": 0, "paused": False, "pause_reason": ""}
    st.update(load_json(STATE, {}))
    return st


def read_topics():
    out = []
    if TOPICS.is_file():
        for line in TOPICS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def parse_topic(line):
    """Separa o marcador de data especial @MM-DD do texto do assunto."""
    m = re.match(r"^@(\d{2})-(\d{2})\s+(.*)$", line.strip())
    if m:
        return "%s-%s" % (m.group(1), m.group(2)), m.group(3).strip()
    return None, line.strip()


def key_of(line):
    return norm(parse_topic(line)[1])


def next_topic(topics, st, today=None):
    """Fila inteligente: data especial de hoje primeiro; depois comuns (sem repetir);
    por fim especiais atrasadas, que voltam quando as comuns acabarem."""
    mmdd = (today or datetime.now().strftime("%m-%d"))
    due_now, commons, late = [], [], []
    for line in topics:
        marker, text = parse_topic(line)
        k = norm(text)
        if k in st["done"] or k in st["failed"] or k in st["pending"]:
            continue
        if marker == mmdd:
            due_now.append(text)
        elif marker:
            late.append(text)
        else:
            commons.append(text)
    if due_now:
        return due_now[0]
    if commons:
        return commons[0]
    if late:
        return late[0]
    return None


def remaining(topics, st):
    return sum(1 for t in topics if key_of(t) not in st["done"] and key_of(t) not in st["failed"]
               and key_of(t) not in st["pending"])


def build_prompt(topic, cfg):
    """Gera o briefing de roteiro usando o prompt_gen embutido (preset Frida e Luna)."""
    minutes = max(1, int(round(cfg["duration_s"] / 60.0)))
    p = prompt_gen.episode_params(topic, duration_s=cfg["duration_s"])
    return prompt_gen.build_script_brief(p)


def stream(cmd, log, hours):
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace", bufsize=1, cwd=str(ROOT), env=env, **kw)
    timer = threading.Timer(hours * 3600, proc.kill)
    timer.daemon = True
    timer.start()
    lines = []
    try:
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            lines.append(line)
            log.raw(line)
        proc.wait()
    finally:
        timer.cancel()
    return proc.returncode, lines


def upload(cfg, topic, video, log):
    title = (topic + cfg["title_suffix"]).strip()[:100]
    desc = cfg["description_template"].replace("{topic}", topic)
    cmd = [sys.executable, str(UPLOADER), "--video", str(video), "--title=" + title, "--description=" + desc,
           "--tags=" + cfg["tags"], "--category=" + str(cfg["category"]), "--privacy=" + cfg["privacy"],
           "--client-secret=" + cfg["client_secret"]]
    if cfg["made_for_kids"]:
        cmd.append("--made-for-kids")
    log("Enviando ao YouTube (%s)..." % cfg["privacy"])
    rc, lines = stream(cmd, log, 2)
    for ln in lines:
        m = re.match(r"OK: (https://youtu\.be/(\S+))", ln)
        if m and rc == 0:
            return True, m.group(1), m.group(2)
    return False, None, None


class Lock:
    def __init__(self, hours):
        self.hours = hours

    def __enter__(self):
        if LOCK.exists() and time.time() - LOCK.stat().st_mtime < (self.hours + 1) * 3600:
            raise SystemExit("Já existe uma execução em andamento (%s). Se for engano, apague esse arquivo." % LOCK)
        LOCK.write_text(str(os.getpid()), encoding="utf-8")
        return self

    def __exit__(self, *a):
        try:
            LOCK.unlink()
        except Exception:
            pass


# -------------------------------------------------------------- execucao ---
def retry_pending(cfg, st, log):
    for k, info in list(st["pending"].items()):
        video = Path(info["video"])
        if not video.is_file():
            log("Pendente sem arquivo, descartando: %s" % info["topic"])
            del st["pending"][k]
            continue
        log("Reenviando vídeo pendente: %s" % info["topic"])
        ok, url, vid = upload(cfg, info["topic"], video, log)
        if ok:
            st["done"][k] = {"topic": info["topic"], "slug": info["slug"], "url": url, "video_id": vid,
                             "date": datetime.now().strftime("%Y-%m-%d")}
            del st["pending"][k]
            log("Pendente enviado: %s" % url)
        save_json(STATE, st)


def run_once(force=False, dry=False, no_upload=False):
    cfg = load_config()
    topics = read_topics()
    st = load_state()
    log = Log()
    today = datetime.now().strftime("%Y-%m-%d")

    if st["paused"] and not dry:
        log("PAUSADO por segurança: %s" % st["pause_reason"])
        log("Corrija o problema e rode: python scripts/daily_runner.py unpause")
        return 2
    if st["last_run_date"] == today and not force and not dry:
        log("Hoje já foi gerado um episódio. Use --force para rodar de novo.")
        return 0
    topic = next_topic(topics, st)
    if topic is None and not (st["pending"] and not dry):
        log("A lista acabou! Acrescente novos assuntos no final de %s" % TOPICS.name)
        return 3

    if dry:
        log("DRY-RUN. Próximo assunto: %s" % topic)
        log("Slug: %s" % make_slug(topic or ""))
        log("Prompt:\n" + build_prompt(topic or "", cfg))
        return 0

    with Lock(cfg["max_hours"]):
        do_upload = cfg["upload"] and not no_upload
        if do_upload and st["pending"]:
            retry_pending(cfg, st, log)
        if topic is None:
            return 3
        left = remaining(topics, st)
        if left <= 7:
            log("ATENÇÃO: restam só %d assuntos na fila. Acrescente mais em %s" % (left, TOPICS.name))

        key, slug = norm(topic), make_slug(topic)
        video = ROOT / "projects" / slug / "output" / ("%s.mp4" % slug)
        prompt = build_prompt(topic, cfg)
        log("=== Episódio: %s  [%s]" % (topic, slug))
        ok = False
        while st["attempts"].get(key, 0) < cfg["max_attempts"]:
            st["attempts"][key] = st["attempts"].get(key, 0) + 1
            save_json(STATE, st)
            log("Tentativa %d de %d (retoma dos checkpoints)" % (st["attempts"][key], cfg["max_attempts"]))
            cmd = [sys.executable, str(PIPELINE), "full", "--prompt", prompt, "--slug", slug,
                   "--duration", str(cfg["duration_s"])] + list(cfg["pipeline_args"])
            rc, _ = stream(cmd, log, cfg["max_hours"])
            if rc == 0 and video.is_file():
                ok = True
                break
            log("Falhou (código %s)." % rc)
            if st["attempts"][key] < cfg["max_attempts"]:
                time.sleep(max(0, cfg["retry_wait_min"]) * 60)

        st["last_run_date"] = today
        if not ok:
            st["failed"][key] = {"topic": topic, "date": today, "reason": "pipeline falhou"}
            st["consecutive_failed"] += 1
            if st["consecutive_failed"] >= cfg["pause_after_failed_topics"]:
                st["paused"] = True
                st["pause_reason"] = "%d assuntos seguidos falharam (veja o log de %s)" % (
                    st["consecutive_failed"], today)
            save_json(STATE, st)
            log("Assunto marcado como falho e pulado: %s" % topic)
            return 1

        st["consecutive_failed"] = 0
        if not do_upload:
            st["done"][key] = {"topic": topic, "slug": slug, "url": None, "date": today}
            log("Vídeo pronto (sem upload): %s" % video)
        else:
            up, url, vid = upload(cfg, topic, video, log)
            if up:
                st["done"][key] = {"topic": topic, "slug": slug, "url": url, "video_id": vid, "date": today}
                log("Publicado: %s" % url)
            else:
                st["pending"][key] = {"topic": topic, "slug": slug, "video": str(video), "date": today}
                log("Upload falhou; o vídeo fica pendente e será reenviado na próxima execução.")
        save_json(STATE, st)
        return 0


def status():
    cfg, topics, st = load_config(), read_topics(), load_state()
    left = remaining(topics, st)
    print("Fila: %d assuntos | feitos: %d | pendentes de upload: %d | falhos: %d | restantes: %d" % (
        len(topics), len(st["done"]), len(st["pending"]), len(st["failed"]), left))
    if st["paused"]:
        print("PAUSADO: %s  (use: unpause)" % st["pause_reason"])
    if left:
        end = datetime.now() + timedelta(days=left)
        print("Com 1 vídeo por dia, a fila acaba em ~%s." % end.strftime("%d/%m/%Y"))
    print("Horário diário: %s | privacidade: %s | upload: %s" % (cfg["time"], cfg["privacy"], cfg["upload"]))
    nxt = []
    for t in topics:
        if key_of(t) not in st["done"] and key_of(t) not in st["failed"] and key_of(t) not in st["pending"]:
            nxt.append(parse_topic(t)[1])
    nxt = nxt[:5]
    if nxt:
        print("\nPróximos:")
        for t in nxt:
            print("  - " + t)
    last = list(st["done"].values())[-5:]
    if last:
        print("\nÚltimos enviados:")
        for d in last:
            print("  - %s  %s  %s" % (d.get("date"), d["topic"], d.get("url") or "(sem upload)"))
    return 0


def loop():
    log = Log()
    log("Modo loop ativo. Ctrl+C para parar.")
    while True:
        cfg = load_config()
        try:
            hh, mm = [int(x) for x in cfg["time"].split(":")]
        except Exception:
            hh, mm = 9, 0
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if load_state()["last_run_date"] == now.strftime("%Y-%m-%d"):
            target += timedelta(days=1)
        elif now > target:
            target = now
        log("Próxima execução: %s" % target.strftime("%d/%m %H:%M"))
        while datetime.now() < target:
            time.sleep(20)
        try:
            rc = run_once()
        except SystemExit as e:
            log(str(e))
            rc = 1
        except Exception as e:
            log("ERRO inesperado: %s" % e)
            rc = 1
        if rc in (2, 3):
            log("Fila parada (código %s). Nova checagem em 1 hora." % rc)
            time.sleep(3600)


def install():
    cfg = load_config()
    if os.name != "nt":
        print("Agendador do Windows só existe no Windows. Use cron, ou o comando 'loop'.")
        return 1
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    runner = pyw if pyw.is_file() else exe
    tr = '"%s" "%s" run' % (runner, Path(__file__).resolve())
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK_NAME, "/SC", "DAILY", "/ST", cfg["time"],
                        "/TR", tr, "/F"], capture_output=True, text=True)
    print(r.stdout or r.stderr)
    if r.returncode == 0:
        print("Tarefa '%s' criada: todo dia às %s." % (TASK_NAME, cfg["time"]))
        print("Dica: no Agendador de Tarefas > Propriedades > Configurações, marque")
        print("'Executar a tarefa o mais rápido possível após uma execução agendada ser perdida'.")
    return r.returncode


def uninstall():
    if os.name != "nt":
        return 1
    r = subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], capture_output=True, text=True)
    print(r.stdout or r.stderr)
    return r.returncode


def unpause(requeue=False):
    st = load_state()
    st.update(paused=False, pause_reason="", consecutive_failed=0)
    if requeue:
        for k in list(st["failed"]):
            st["attempts"].pop(k, None)
        n = len(st["failed"])
        st["failed"] = {}
        print("%d assunto(s) falho(s) voltaram para a fila." % n)
    save_json(STATE, st)
    print("Fila liberada.")
    return 0


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Executor diário do Videomaker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="gera e envia o próximo episódio")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--no-upload", action="store_true")
    r.add_argument("--force", action="store_true")
    for name in ("status", "loop", "install", "uninstall"):
        sub.add_parser(name)
    u = sub.add_parser("unpause", help="libera a fila pausada")
    u.add_argument("--requeue-failed", action="store_true", help="recoloca na fila os assuntos que falharam")
    a = ap.parse_args()
    if a.cmd == "run":
        return run_once(force=a.force, dry=a.dry_run, no_upload=a.no_upload)
    if a.cmd == "unpause":
        return unpause(a.requeue_failed)
    return {"status": status, "loop": loop, "install": install, "uninstall": uninstall}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
