# -*- coding: utf-8 -*-
"""
Videomaker - Backend API Premium (FastAPI).
Expõe o pipeline Python como REST + WebSocket para o frontend React.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "scripts"
PIPELINE = SCRIPTS / "pipeline.py"
DAILY = SCRIPTS / "daily_runner.py"
TOPICS = SCRIPTS / "topics.txt"
SCHEDULE_FILE = ROOT / "scheduled_videos.json"
SETTINGS_FILE = ROOT / "user_settings.json"
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = sys.executable

app = FastAPI(title="Videomaker Premium API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ estado ---
active_runs: dict = {}  # run_id -> {proc, log_queue, status, start_time, upload_proc, stopping}
ws_clients: list = []
log_buffer: list = []   # últimos N eventos para hidratar o frontend
_main_loop = None
LOG_BUFFER_MAX = 800

# ------------------------------------------------------------------ helpers ---
def _kill_tree(pid: int) -> bool:
    """Mata a árvore de processos no Windows (taskkill /F /T /PID)."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True, timeout=10
        )
        return True
    except Exception:
        return False


def _subprocess_env():
    """Env padrão para subprocessos: unbuffered + utf-8."""
    return {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}


def _creation_flags():
    """Flags de criação no Windows para permitir kill tree."""
    if sys.platform == "win32":
        return subprocess.CREATE_NEW_PROCESS_GROUP
    return 0


@app.on_event("startup")
async def _capture_loop():
    global _main_loop
    _main_loop = asyncio.get_running_loop()
    threading.Thread(target=_scheduler_loop, daemon=True).start()
    log_msg("[api] backend premium iniciado (scheduler ativo)", "ok")


def _ws_push(ws, payload: str):
    async def _send():
        try:
            await ws.send_text(payload)
        except Exception:
            pass
    if _main_loop is not None and not _main_loop.is_closed():
        asyncio.run_coroutine_threadsafe(_send(), _main_loop)


def log_msg(msg: str, level: str = "info"):
    payload = {"ts": datetime.now().isoformat(), "level": level, "msg": msg}
    body = json.dumps(payload, ensure_ascii=False)
    log_buffer.append(payload)
    if len(log_buffer) > LOG_BUFFER_MAX:
        del log_buffer[: len(log_buffer) - LOG_BUFFER_MAX]
    for ws in list(ws_clients):
        try:
            if _main_loop is not None and not _main_loop.is_closed():
                _ws_push(ws, body)
            else:
                asyncio.create_task(ws.send_text(body))
        except Exception:
            pass
    try:
        print(msg, flush=True)
    except Exception:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def slugify(text: str) -> str:
    import unicodedata
    if not text:
        return "projeto"
    slug = unicodedata.normalize("NFKD", text.lower().strip())
    slug = "".join(c for c in slug if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")[:40].strip("-")
    return slug or "projeto"


def list_projects():
    out = []
    proj_dir = ROOT / "projects"
    if not proj_dir.exists():
        return out
    for d in sorted(proj_dir.iterdir()):
        if not d.is_dir():
            continue
        state_file = d / "project.json"
        video = d / "output" / f"{d.name}.mp4"
        state = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        phases = state.get("phases", {})
        done = sum(1 for v in phases.values() if v.get("done"))
        yt = state.get("youtube") or {}
        out.append({
            "slug": d.name,
            "prompt": state.get("prompt", ""),
            "done": done,
            "total": 10,
            "video": str(video) if video.exists() else None,
            "video_exists": video.exists(),
            "youtube_url": yt.get("url"),
            "published": bool(yt.get("url")),
            "updated": state.get("phases", {}).get("render", {}).get("ts", ""),
        })
    return out


# ------------------------------------------------------------------ telemetry ---
def _project_phases_with_durations(slug: str):
    """Lê project.json e calcula durações entre fases consecutivas."""
    state_file = ROOT / "projects" / slug / "project.json"
    if not state_file.exists():
        return {}, {}
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}
    phases = state.get("phases", {})
    # ordem canônica das fases
    phase_order = ["script", "scenes", "images", "music", "narration", "timeline", "mix", "compose", "preprocess", "render"]
    phase_data = {}
    prev_ts = None
    for ph in phase_order:
        p = phases.get(ph)
        if p and p.get("done"):
            ts_str = p.get("ts")
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                ts = None
            dur = None
            if prev_ts and ts:
                dur = round((ts - prev_ts).total_seconds(), 1)
            phase_data[ph] = {"done": True, "ts": ts_str, "duration_s": dur, "detail": p.get("detail", "")}
            if ts:
                prev_ts = ts
        else:
            phase_data[ph] = {"done": False, "ts": None, "duration_s": None, "detail": ""}
    return phase_data, state


DEFAULT_USER_SETTINGS = {
    "pipeline": {
        "duration": 590,
        "voice": "pt-BR-ThalitaNeural",
        "rate": "+12%",
        "pitch": "+8Hz",
        "no_parallel": False,
        "skip_check": False,
        "publish": False,
    },
    "youtube": {
        "privacy": "private",
        "category": "24",
        "tags": "cachorro,animação,frida,luna",
        "kids": False,
        "mode": "manual",
    },
}


def load_user_settings() -> dict:
    out = json.loads(json.dumps(DEFAULT_USER_SETTINGS))
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return out
    for k, v in (data or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v or {})
        else:
            out[k] = v
    return out


def save_user_settings(data: dict) -> dict:
    cur = load_user_settings()
    for k, v in (data or {}).items():
        if isinstance(v, dict) and isinstance(cur.get(k), dict):
            cur[k].update(v or {})
        else:
            cur[k] = v
    SETTINGS_FILE.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    return cur


class UserSettingsBody(BaseModel):
    pipeline: Optional[dict] = None
    youtube: Optional[dict] = None


@app.get("/api/settings")
def api_get_settings():
    return load_user_settings()


@app.put("/api/settings")
def api_put_settings(body: UserSettingsBody):
    payload = {}
    if body.pipeline is not None:
        payload["pipeline"] = body.pipeline
    if body.youtube is not None:
        payload["youtube"] = body.youtube
    return save_user_settings(payload)


@app.get("/api/telemetry")
def api_telemetry():
    """Agrega métricas de todos os projetos para painel executivo."""
    projects = []
    completed = 0
    total_duration = 0.0
    proj_dir = ROOT / "projects"
    if not proj_dir.exists():
        return {
            "generated_at": datetime.now().isoformat(),
            "kpis": {"total_projects": 0, "completed": 0, "success_rate": 0, "avg_duration_s": 0},
            "projects": [],
            "active_runs": [_run_public(k, v) for k, v in active_runs.items()
                            if v.get("status") in ("running", "starting", "uploading")],
        }
    for d in sorted(proj_dir.iterdir()):
        if not d.is_dir():
            continue
        slug = d.name
        phase_data, state = _project_phases_with_durations(slug)
        video = ROOT / "projects" / slug / "output" / f"{slug}.mp4"
        # duração total do projeto (primeira fase done até última fase done)
        done_phases = [(ph, pd) for ph, pd in phase_data.items() if pd.get("done")]
        proj_duration = 0.0
        try:
            if len(done_phases) >= 2:
                first_ts = datetime.strptime(done_phases[0][1]["ts"], "%Y-%m-%d %H:%M:%S")
                last_ts = datetime.strptime(done_phases[-1][1]["ts"], "%Y-%m-%d %H:%M:%S")
                proj_duration = round((last_ts - first_ts).total_seconds(), 1)
            elif len(done_phases) == 1:
                proj_duration = done_phases[0][1].get("duration_s") or 0
        except Exception:
            proj_duration = 0.0
        if video.exists():
            completed += 1
            total_duration += proj_duration
        projects.append({
            "slug": slug,
            "prompt": state.get("prompt", ""),
            "phases": phase_data,
            "video_exists": video.exists(),
            "video_path": str(video) if video.exists() else None,
            "total_duration_s": proj_duration,
            "last_activity": max((pd.get("ts") for pd in phase_data.values() if pd.get("ts")), default=""),
        })
    total = len(projects)
    success_rate = round((completed / total * 100), 1) if total else 0
    avg_duration = round(total_duration / completed, 1) if completed else 0
    return {
        "generated_at": datetime.now().isoformat(),
        "kpis": {
            "total_projects": total,
            "completed": completed,
            "success_rate": success_rate,
            "avg_duration_s": avg_duration,
        },
        "projects": projects,
        "active_runs": [_run_public(k, v) for k, v in active_runs.items()
                        if v.get("status") in ("running", "starting", "uploading")],
    }
class PipelineRun(BaseModel):
    prompt: str
    mode: str = "auto"          # auto, from, only, skip
    phases: Optional[str] = None  # "script,scenes" etc.
    from_phase: Optional[str] = None
    force: bool = False
    no_parallel: bool = False
    skip_check: bool = False
    voice: str = "pt-BR-ThalitaNeural"
    rate: str = "+12%"
    pitch: str = "+8Hz"
    style: str = "excited"
    wait: str = "240"
    duration: int = 590
    upload: Optional[bool] = None
    # --- YouTube metadata (usado quando upload=True) ---
    yt_title: str = ""
    yt_desc: str = ""
    yt_tags: str = "pixel art,animação,cachorro,divertido"
    yt_mode: str = "manual"     # manual, auto, ask
    yt_priv: str = "private"    # private, unlisted, public
    yt_cat: str = "24"
    yt_when: str = ""           # AAAA-MM-DD HH:MM
    yt_kids: bool = False
    yt_thumb: str = ""
    yt_secret: str = ""
    yt_video: str = ""


class ScheduleCreate(BaseModel):
    date: str      # YYYY-MM-DD
    time: str      # HH:MM
    prompt: str = ""
    source: str = "topic"      # topic = tema escolhido | queue = fila automática
    recurrence: str = "none"   # none, daily, weekdays, weekly
    weekdays: list = []
    dry: bool = False


# ------------------------------------------------------------------ schedulers ---
LEGACY_SCHEDULE_FILE = SCRIPTS / "scheduled_videos.json"


def load_schedules():
    data = {"scheduled_videos": []}
    try:
        data = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    # migração: puxa agendamentos criados pela UI tkinter no caminho antigo
    if LEGACY_SCHEDULE_FILE.exists():
        try:
            old = json.loads(LEGACY_SCHEDULE_FILE.read_text(encoding="utf-8"))
            known = {s.get("id") for s in data.get("scheduled_videos", [])}
            migrated = []
            for s in old.get("scheduled_videos", []):
                if s.get("id") and s.get("id") not in known:
                    s.setdefault("source", "topic" if (s.get("prompt") or "").strip() else "queue")
                    data.setdefault("scheduled_videos", []).append(s)
                    migrated.append(s.get("id"))
            if migrated:
                save_schedules(data)
                log_msg(f"[scheduler] migrados {len(migrated)} agendamento(s) de scripts/ → raiz: {migrated}", "warn")
                try:
                    LEGACY_SCHEDULE_FILE.rename(LEGACY_SCHEDULE_FILE.with_suffix(".json.migrated"))
                except Exception:
                    pass
        except Exception:
            pass
    return data


def save_schedules(data):
    try:
        SCHEDULE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# -------------------------------------------------------------- scheduler ----
_scheduler_fired: dict = {}   # schedule_id -> "YYYY-MM-DD HH:MM" do último slot disparado
_last_fire_ts = 0.0
FIRE_GAP_S = 45  # não iniciar dois pipelines do scheduler com menos de 45s de diferença
SCHEDULER_TICK = 15  # segundos entre checagens


def _next_recurrence_date(s):
    rec = s.get("recurrence", "none")
    try:
        d = datetime.strptime(s["date"], "%Y-%m-%d")
    except Exception:
        return None
    while True:
        d += timedelta(days=7) if rec == "weekly" else timedelta(days=1)
        if rec != "weekdays" or d.weekday() < 5:
            break
    return d


def _fire_schedule(entry: dict):
    """Dispara o agendamento: fila automática (daily_runner) ou prompt específico (pipeline)."""
    run_id = str(uuid.uuid4())[:8]
    sid = entry.get("id")
    if entry.get("source") == "queue" or not entry.get("prompt", "").strip():
        prompt = "fila automatica (proximo da fila)"
        cmd = [str(PYTHON_EXE), str(DAILY), "run", "--force"]
        if entry.get("dry"):
            cmd.append("--dry-run")
        active_runs[run_id] = {"status": "starting", "proc": None,
                               "slug": "daily", "prompt": prompt, "schedule_id": sid}
        threading.Thread(target=run_pipeline_subprocess, args=(run_id, cmd), daemon=True).start()
        log_msg(f"[scheduler] fila automatica disparada ({slot_str(entry)}) — run {run_id}", "ok")
        return
    prompt = (entry.get("prompt") or "").strip()
    slug = slugify(prompt)
    body = PipelineRun(prompt=prompt, upload=bool(entry.get("upload", False)))
    cmd = [str(PYTHON_EXE), str(PIPELINE), "full", "--prompt", prompt,
           "--voice", body.voice, "--rate", body.rate, "--pitch", body.pitch,
           "--style", body.style, "--wait", body.wait,
           "--duration", str(body.duration)]
    active_runs[run_id] = {"status": "starting", "proc": None,
                           "slug": slug, "prompt": prompt, "schedule_id": sid}
    threading.Thread(target=run_pipeline_subprocess, args=(run_id, cmd, body), daemon=True).start()
    log_msg(f"[scheduler] agendamento {sid} disparado ({slot_str(entry)}) — run {run_id}: {prompt[:60]}", "ok")


def slot_str(s):
    return f"{s.get('date','?')} {s.get('time','?')}"


def _scheduler_loop():
    global _last_fire_ts
    log_msg("[scheduler] monitor de agendamentos ativo", "ok")
    while True:
        time.sleep(SCHEDULER_TICK)
        try:
            now = datetime.now()
            data = load_schedules()
            changed = False
            for entry in list(data.get("scheduled_videos", [])):
                if entry.get("done"):
                    continue
                try:
                    dt = datetime.strptime(slot_str(entry), "%Y-%m-%d %H:%M")
                except Exception:
                    continue
                if now < dt:
                    continue
                sid = entry.get("id")
                if sid and _scheduler_fired.get(sid) == slot_str(entry):
                    continue
                # não iniciar se já há pipeline ativo (Chrome CDP é single-user)
                busy = any(
                    r.get("status") in ("running", "starting", "uploading")
                    for r in active_runs.values()
                )
                if busy:
                    log_msg(f"[scheduler] run ativo em andamento; adiando {sid} ({slot_str(entry)})", "info")
                    continue
                # stagger: não iniciar dois pipelines quase juntos
                if time.time() - _last_fire_ts < FIRE_GAP_S:
                    log_msg(f"[scheduler] aguardando gap para disparar {sid} ({slot_str(entry)})", "info")
                    continue
                _last_fire_ts = time.time()
                _scheduler_fired[sid] = slot_str(entry)
                _fire_schedule(entry)
                nxt = _next_recurrence_date(entry) if entry.get("recurrence") in ("daily", "weekdays", "weekly") else None
                if nxt is not None:
                    entry["date"] = nxt.strftime("%Y-%m-%d")
                    entry["done"] = False
                    log_msg(f"[scheduler] recorrência '{entry['recurrence']}' reagendada para {entry['date']} {entry['time']}", "info")
                else:
                    entry["done"] = True
                changed = True
            if changed:
                save_schedules(data)
        except Exception as e:
            try:
                log_msg(f"[scheduler] erro no ciclo: {e}", "err")
            except Exception:
                pass


# ------------------------------------------------------------------ execução ---
UPLOADER = SCRIPTS / "youtube_upload.py"

PHASE_ORDER = ["script", "scenes", "images", "music", "narration",
               "timeline", "mix", "compose", "preprocess", "render"]


def _track_phase(rec: dict, line: str):
    """Atualiza fase corrente do run a partir do stdout do pipeline."""
    m = re.search(r"IMAGEM\s+(\d+)\s*/\s*(\d+)", line)
    if m:
        rec["detail"] = f"imagem {m.group(1)}/{m.group(2)}"
        rec.setdefault("phases", {})
        rec["phases"]["images"] = {"done": False, "running": True}
        rec["current_phase"] = "images"
        return
    m = re.search(r"QUARENTENA", line, re.IGNORECASE)
    if m:
        rec["detail"] = "quarentena de imagens"
        rec["current_phase"] = "images"
        return
    m = re.search(r"FASE\s+([a-z]+)", line, re.IGNORECASE)
    if m:
        ph = m.group(1).lower()
        if ph in PHASE_ORDER:
            prev = rec.get("current_phase")
            if prev and prev != ph and isinstance(rec.get("phases"), dict):
                rec["phases"][prev] = {"done": True, "running": False}
            rec["current_phase"] = ph
            rec["detail"] = None
            rec.setdefault("phases", {})[ph] = {
                "done": False, "running": True, "started_at": datetime.now().isoformat(),
            }
            return
    m = re.search(r"CHECKPOINT\s+([a-z]+).*(pulando|feito)", line, re.IGNORECASE)
    if m:
        ph = m.group(1).lower()
        if ph in PHASE_ORDER:
            rec.setdefault("phases", {}).setdefault(ph, {})
            rec["phases"][ph] = {"done": True, "running": False, "skipped": True}
            if rec.get("current_phase") is None:
                rec["current_phase"] = ph


def _mark_youtube(slug: str, url: str, video_id: str):
    """Grava o link do YouTube no project.json do slug."""
    if not slug or slug == "daily":
        return
    sf = ROOT / "projects" / slug / "project.json"
    if not sf.exists():
        return
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except Exception:
        return
    st["youtube"] = {
        "url": url,
        "video_id": video_id,
        "published": True,
        "published_at": datetime.now().isoformat(),
    }
    try:
        sf.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def run_pipeline_subprocess(run_id: str, cmd: list, body: Optional[PipelineRun] = None):
    rec = active_runs[run_id]
    rec["status"] = "running"
    rec["start_time"] = time.time()
    rec["stopping"] = False
    rec["current_phase"] = None
    rec["phases"] = {}
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(ROOT),
            encoding="utf-8",
            errors="replace",
            env=_subprocess_env(),
            creationflags=_creation_flags(),
        )
        rec["proc"] = proc
        for line in proc.stdout:
            if rec.get("stopping"):
                break
            line = line.rstrip("\n")
            if line:
                log_msg(f"[pipeline] {line}")
                _track_phase(rec, line)
        proc.wait()
        if rec.get("stopping"):
            rec["status"] = "stopped"
            log_msg(f"[pipeline] interrompido pelo usuário (run {run_id})", "warn")
            return
        if proc.returncode == 0:
            rec["status"] = "ok"
            if rec.get("current_phase"):
                rec.setdefault("phases", {})[rec["current_phase"]] = {"done": True, "running": False}
            log_msg(f"[pipeline] concluído com sucesso (run {run_id})", "ok")
            slug = rec.get("slug") or ""
            # --- upload separado para o YouTube ---
            if body and body.upload:
                rec["status"] = "uploading"
                upload_cmd, video = build_upload_cmd(body)
                if upload_cmd is None:
                    rec["status"] = "error"
                    log_msg(f"[upload] vídeo não encontrado: {video}", "err")
                    log_msg("YOUTUBE: NÃO PUBLICADO — arquivo MP4 não encontrado. Publique manualmente em Publicar.", "err")
                    return
                log_msg(f"[upload] iniciando envio ao YouTube (run {run_id})")
                up = subprocess.Popen(
                    upload_cmd,
                    cwd=str(ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=_subprocess_env(),
                    creationflags=_creation_flags(),
                )
                rec["upload_proc"] = up
                for line in up.stdout:
                    if rec.get("stopping"):
                        break
                    line = line.rstrip("\n")
                    if line.strip():
                        log_msg(f"[upload] {line}")
                    m = re.match(r"OK: (https://youtu\.be/(\S+))", line)
                    if m:
                        rec["youtube_url"] = m.group(1)
                        rec["youtube_id"] = m.group(2)
                up.wait()
                if rec.get("stopping"):
                    rec["status"] = "stopped"
                    log_msg(f"[upload] interrompido pelo usuário (run {run_id})", "warn")
                    return
                if up.returncode == 0:
                    rec["status"] = "ok"
                    url = rec.get("youtube_url")
                    if url:
                        _mark_youtube(slug, url, rec.get("youtube_id") or "")
                        log_msg(f"YOUTUBE: PUBLICADO COM SUCESSO — link do vídeo no YouTube é {url} (run {run_id})", "ok")
                    else:
                        log_msg(f"[upload] enviado com sucesso (run {run_id})", "ok")
                        log_msg("YOUTUBE: upload terminou sem link de retorno. Confira no YouTube Studio.", "warn")
                else:
                    rec["status"] = "error"
                    log_msg(f"[upload] falhou código {up.returncode} (run {run_id})", "err")
                    log_msg("YOUTUBE: NÃO PUBLICADO — falha no envio. Tente novamente em Publicar.", "err")
            else:
                video = ROOT / "projects" / slug / "output" / f"{slug}.mp4" if slug and slug != "daily" else None
                if video and video.exists():
                    log_msg(f"YOUTUBE: NÃO PUBLICADO — vídeo '{slug}' concluído mas não foi enviado ao YouTube. "
                            f"Publique na página Publicar ou rode scripts/youtube_upload.py --video \"{video}\"", "warn")
                elif slug == "daily":
                    log_msg("YOUTUBE: NÃO PUBLICADO — diário concluído (upload depende da config do daily_runner).", "warn")
        else:
            rec["status"] = "error"
            log_msg(f"[pipeline] falhou com código {proc.returncode} (run {run_id})", "err")
    except Exception as e:
        rec["status"] = "error"
        log_msg(f"[pipeline] erro: {e}", "err")
    finally:
        rec["proc"] = None
        rec["upload_proc"] = None


def build_upload_cmd(body: PipelineRun):
    """Monta o comando youtube_upload.py a partir dos campos do body."""
    import unicodedata
    slug = slugify(body.prompt)
    video = body.yt_video.strip() or str(ROOT / "projects" / slug / "output" / f"{slug}.mp4")
    from pathlib import Path
    if not Path(video).is_file():
        return None, video
    prompt = body.prompt.strip()
    title = body.yt_title.strip() or (prompt.split("\n")[0][:100] if prompt else Path(video).stem)
    desc = body.yt_desc.strip() or prompt
    cmd = [
        str(PYTHON_EXE), str(UPLOADER),
        "--video", video,
        "--title=" + title,
        "--description=" + desc,
        "--tags=" + body.yt_tags.strip(),
        "--category=" + (body.yt_cat.strip() or "24"),
        "--privacy=" + body.yt_priv,
        "--client-secret=" + (body.yt_secret.strip() or str(SCRIPTS / "client_secret.json")),
    ]
    if body.yt_kids:
        cmd.append("--made-for-kids")
    if body.yt_when.strip():
        cmd.append("--publish-at=" + body.yt_when.strip())
    if body.yt_thumb.strip():
        cmd.append("--thumbnail=" + body.yt_thumb.strip())
    return cmd, video


@app.post("/api/pipeline/run")
def api_pipeline_run(body: PipelineRun):
    run_id = str(uuid.uuid4())[:8]
    slug = slugify(body.prompt)
    cmd = [str(PYTHON_EXE), str(PIPELINE), "full", "--prompt", body.prompt]
    if body.mode == "from" and body.from_phase:
        cmd += ["--from", body.from_phase]
    if body.mode == "only" and body.phases:
        cmd += ["--only", body.phases]
    if body.mode == "skip" and body.phases:
        cmd += ["--skip", body.phases]
    if body.force:
        cmd.append("--force")
    if body.no_parallel:
        cmd.append("--no-parallel")
    if body.skip_check:
        cmd.append("--skip-check")
    cmd += ["--voice", body.voice, "--rate", body.rate, "--pitch", body.pitch]
    if body.style:
        cmd += ["--style", body.style]
    cmd += ["--wait", body.wait, "--duration", str(body.duration)]

    active_runs[run_id] = {"status": "starting", "proc": None, "slug": slug, "prompt": body.prompt}
    t = threading.Thread(target=run_pipeline_subprocess, args=(run_id, cmd, body), daemon=True)
    t.start()
    return {"run_id": run_id, "slug": slug, "status": "starting"}


@app.post("/api/pipeline/resume")
def api_pipeline_resume(slug: str, force: bool = False, from_phase: str = None):
    run_id = str(uuid.uuid4())[:8]
    cmd = [str(PYTHON_EXE), str(PIPELINE), "resume", "--slug", slug]
    if force:
        cmd.append("--force")
    if from_phase:
        cmd += ["--from", from_phase]
    active_runs[run_id] = {"status": "starting", "proc": None, "slug": slug, "prompt": ""}
    t = threading.Thread(target=run_pipeline_subprocess, args=(run_id, cmd), daemon=True)
    t.start()
    return {"run_id": run_id, "slug": slug, "status": "starting"}


@app.get("/api/pipeline/status/{run_id}")
def api_pipeline_status(run_id: str):
    rec = active_runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="run não encontrado")
    return _run_public(run_id, rec)


def _run_public(run_id: str, rec: dict) -> dict:
    """Serializa o run sem objetos Popen (não JSON-serializável)."""
    return {
        "run_id": run_id,
        "status": rec.get("status"),
        "slug": rec.get("slug", ""),
        "prompt": rec.get("prompt", ""),
        "current_phase": rec.get("current_phase"),
        "detail": rec.get("detail"),
        "phases": rec.get("phases") or {},
        "elapsed": round(time.time() - rec.get("start_time", 0), 1) if rec.get("start_time") else 0,
        "stopping": bool(rec.get("stopping")),
    }


@app.get("/api/pipeline/runs")
def api_pipeline_runs():
    return [_run_public(k, v) for k, v in active_runs.items()]


@app.post("/api/pipeline/stop/{run_id}")
def api_pipeline_stop(run_id: str):
    rec = active_runs.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="execução não encontrada")
    rec["stopping"] = True
    killed = False
    for proc_key in ("proc", "upload_proc"):
        proc = rec.get(proc_key)
        if proc and hasattr(proc, "pid"):
            if _kill_tree(proc.pid):
                killed = True
    rec["status"] = "stopped"
    cur = rec.get("current_phase")
    if cur and isinstance(rec.get("phases"), dict) and cur in rec["phases"]:
        rec["phases"][cur] = {**rec["phases"][cur], "running": False, "done": False}
    log_msg(f"[api] run {run_id} parado (kill_tree={killed})", "warn")
    return {"ok": True, "killed": killed}


@app.post("/api/pipeline/stop-all")
def api_pipeline_stop_all():
    results = []
    for run_id, rec in list(active_runs.items()):
        if rec.get("status") in ("running", "starting", "uploading"):
            rec["stopping"] = True
            killed = False
            for proc_key in ("proc", "upload_proc"):
                proc = rec.get(proc_key)
                if proc and hasattr(proc, "pid"):
                    if _kill_tree(proc.pid):
                        killed = True
            rec["status"] = "stopped"
            results.append({"run_id": run_id, "killed": killed})
    log_msg(f"[api] stop-all: {len(results)} runs interrompidos", "warn")
    return {"ok": True, "stopped": results}


# ------------------------------------------------------------------ daily: stop-agent / agent-status / unpause-requeue ---
@app.post("/api/daily/stop-agent")
def api_daily_stop_agent():
    """Mata processos externos (schtasks/loop) que rodam daily_runner.py ou pipeline.py."""
    killed_pids = []
    try:
        # PowerShell para achar processos python com cmdline contendo daily_runner/pipeline
        ps_cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
            "Where-Object { $_.CommandLine -match 'daily_runner\\.py|pipeline\\.py' } | "
            "Select-Object -ExpandProperty ProcessId"
        ]
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=15)
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if _kill_tree(pid):
                    killed_pids.append(pid)
    except Exception as e:
        log_msg(f"[api] stop-agent erro: {e}", "err")
    log_msg(f"[api] stop-agent: {len(killed_pids)} processos externos mortos", "warn")
    return {"ok": True, "killed_pids": killed_pids}


@app.get("/api/daily/agent-status")
def api_daily_agent_status():
    """Detecta agentes externos (schtasks/loop) rodando sem run_id no API."""
    pids = []
    try:
        ps_cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
            "Where-Object { $_.CommandLine -match 'daily_runner\\.py|pipeline\\.py' } | "
            "Select-Object -ExpandProperty ProcessId"
        ]
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=10)
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                pids.append(int(line))
    except Exception:
        pass
    return {"active": len(pids) > 0, "pids": pids, "hint": "schtasks loop ou daily_runner externo" if pids else "nenhum agente externo detectado"}


@app.post("/api/daily/unpause-requeue")
def api_daily_unpause_requeue():
    """Chama daily_runner unpause --requeue-failed (recoloca assunto falho na fila)."""
    try:
        out = subprocess.check_output(
            [str(PYTHON_EXE), str(DAILY), "unpause", "--requeue-failed"],
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=30
        )
        log_msg(f"[api] unpause-requeue: {out.strip()}", "ok")
        return {"ok": True, "output": out.strip()}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": e.output or "falha ao requeue"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------------ projetos ---
@app.get("/api/projects")
def api_projects():
    return list_projects()


@app.get("/api/projects/{slug}/status")
def api_project_status(slug: str):
    state_file = ROOT / "projects" / slug / "project.json"
    video = ROOT / "projects" / slug / "output" / f"{slug}.mp4"
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    phases = state.get("phases", {})
    return {
        "slug": slug,
        "prompt": state.get("prompt", ""),
        "phases": phases,
        "video_exists": video.exists(),
        "video_path": str(video) if video.exists() else None,
    }


# ------------------------------------------------------------------ diário ---
class DailyRun(BaseModel):
    force: bool = False
    dry_run: bool = False
    no_upload: bool = False


@app.post("/api/daily/run")
def api_daily_run(force: bool = False, dry_run: bool = False, no_upload: bool = False,
                  body: Optional[DailyRun] = None):
    if body is not None:  # o frontend envia as flags como JSON body
        force = force or body.force
        dry_run = dry_run or body.dry_run
        no_upload = no_upload or body.no_upload
    run_id = str(uuid.uuid4())[:8]
    cmd = [str(PYTHON_EXE), str(DAILY), "run"]
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")
    if no_upload:
        cmd.append("--no-upload")
    active_runs[run_id] = {"status": "starting", "proc": None, "slug": "daily", "prompt": "fila automatica"}
    t = threading.Thread(target=run_pipeline_subprocess, args=(run_id, cmd), daemon=True)
    t.start()
    return {"run_id": run_id, "status": "starting"}


@app.get("/api/daily/status")
def api_daily_status():
    try:
        out = subprocess.check_output([str(PYTHON_EXE), str(DAILY), "status"],
                                      stderr=subprocess.STDOUT, text=True,
                                      encoding="utf-8", errors="replace", timeout=15)
    except subprocess.CalledProcessError as e:
        out = e.output or "Erro ao obter status"
    except Exception as e:
        out = f"Erro: {e}"
    return {"output": out}


# ------------------------------------------------------------------ agendamento ---
@app.get("/api/schedules")
def api_schedules():
    return load_schedules()


@app.post("/api/schedules")
def api_create_schedule(body: ScheduleCreate):
    data = load_schedules()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "date": body.date,
        "time": body.time,
        "prompt": (body.prompt or "").strip(),
        "source": body.source if body.source in ("topic", "queue") else "topic",
        "recurrence": body.recurrence,
        "weekdays": body.weekdays,
        "dry": body.dry,
        "created_at": datetime.now().isoformat(),
        "done": False,
    }
    data["scheduled_videos"].append(entry)
    save_schedules(data)
    return entry


@app.delete("/api/schedules/{schedule_id}")
def api_delete_schedule(schedule_id: str):
    data = load_schedules()
    data["scheduled_videos"] = [s for s in data["scheduled_videos"] if s.get("id") != schedule_id]
    save_schedules(data)
    return {"ok": True}


@app.post("/api/schedules/{schedule_id}/done")
def api_mark_done(schedule_id: str):
    data = load_schedules()
    for s in data["scheduled_videos"]:
        if s.get("id") == schedule_id:
            s["done"] = True
    save_schedules(data)
    return {"ok": True}


# ------------------------------------------------------------------ tópicos ---
@app.get("/api/topics")
def api_topics():
    if not TOPICS.exists():
        return []
    lines = []
    for line in TOPICS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


@app.get("/api/logs/recent")
def api_logs_recent(limit: int = 200):
    """Últimos eventos de log para hidratar o painel antes do WS Fluxo vivo."""
    limit = max(1, min(800, limit))
    return {"logs": log_buffer[-limit:], "total": len(log_buffer)}


# ------------------------------------------------------------------ websocket ---
@app.websocket("/api/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        # hidrata o cliente com o histórico recente
        for payload in log_buffer[-200:]:
            try:
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                break
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in ws_clients:
            ws_clients.remove(websocket)


# ------------------------------------------------------------------ root ---
@app.get("/api/health")
def api_health():
    return {"ok": True, "version": "3.0.0", "python": sys.version}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
