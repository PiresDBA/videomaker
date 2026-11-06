# -*- coding: utf-8 -*-
"""
Orquestrador do pipeline de video com checkpoints e retomada.

Cada rodada cria um projeto proprio em:

  <raiz>/projects/<slug>/

onde <slug> vem do ASSUNTO/PROMPT pedido pelo usuario. Todo o conteudo fica
la dentro (roteiro, cenas, imagens, musica, narracao, mix, composicao e video),
e um arquivo `project.json` funciona como controle de memoria (checkpoints):
se o pipeline parar no meio, rodar de novo retoma de onde parou.

Diretorio por projeto:

  projects/<slug>/project.json                    checkpoints + historico
  projects/<slug>/artifacts/script.json           roteiro (IA gratuita via Chrome)
  projects/<slug>/artifacts/scenes.json           cenas (local, deterministico)
  projects/<slug>/artifacts/image_prompts.json    prompts de imagem
  projects/<slug>/artifacts/narration_timing.json duracoes da narracao
  projects/<slug>/artifacts/timeline.json         inicio/fim por secao
  projects/<slug>/scenes/sN.html                  overlays de texto por cena
  projects/<slug>/assets/images/gemini/scenes/*.jpg
  projects/<slug>/assets/audio/gemini/bgm_gemini.wav  trilha (IA gratuita)
  projects/<slug>/assets/audio/narration/*.mp3    narracao Edge-TTS (local)
  projects/<slug>/assets/audio/narration_full.wav narracao concatenada
  projects/<slug>/assets/audio/final_mix.m4a      narracao + trilha
  projects/<slug>/composition.html                composicao HyperFrames
  projects/<slug>/output/<slug>.mp4               VIDEO FINAL

Uso (CLI):
  Rodar tudo automatico (retoma de onde parou):
    python scripts/pipeline.py full --prompt "Vidoe engraçado sobre buldogue ingles"
  Começar de uma fase especifica:
    python scripts/pipeline.py full --prompt P --from narration
  Rodar somente determinadas fases:
    python scripts/pipeline.py full --prompt P --only mix,compose
  Pular fases:
    python scripts/pipeline.py full --prompt P --skip music
  Ignorar checkpoints e refazer:
    python scripts/pipeline.py full --prompt P --from script --force
  Ver status dos checkpoints:
    python scripts/pipeline.py status --prompt P
  Resetar checkpoints de uma fase (refaz na proxima rodada):
    python scripts/pipeline.py reset --prompt P --phase images
  Retomar projeto ja existente pelo slug (sem prompt):
    python scripts/pipeline.py resume --slug buldogue-ingles
Fases: script, scenes, images, music, narration, timeline, mix, compose,
       preprocess, render
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from narration_contract import validate_contract

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HF_DIR = ROOT / "hyperframes-workspace"

# Bancos locais de mídia (imagens e músicas) para reuso antes de gerar via Gemini
BANCO_IMAGENS = ROOT / "banco de imagens"
BANCO_MUSICAS = ROOT / "banco de musicas"
DB_IMAGENS = BANCO_IMAGENS / "indice_midia.db"

# Rotação de músicas: só usa o banco quando houver um acervo mínimo e nunca
# repete uma trilha já usada em outro projeto (LRU quando o acervo esgota).
MIN_MUSICAS_BANCO = 20
MUSICAS_CONTROLE = BANCO_MUSICAS / "musicas_controle.json"

# Adiciona o diretório do banco de imagens ao path para importar o buscador
sys.path.insert(0, str(BANCO_IMAGENS))
try:
    from indexar_midia import abrir_db, normalizar_texto as _nt, slug as _slug
except Exception:
    abrir_db = None
    _nt = None
    _slug = None

PHASES = ["script", "scenes", "music", "images", "narration",
          "timeline", "mix", "compose", "preprocess", "render"]

SCRIPTS = {
    "script_from_prompt": HERE / "generate_script_from_prompt.py",
    "scenes_from_script": HERE / "generate_scenes_and_prompts.py",
    "scene_htmls": HERE / "generate_scene_htmls.py",
    "fetch_images": HERE / "fetch_images.py",
    "preprocess_images": HERE / "preprocess_images.py",
    "fetch_music": HERE / "fetch_music_gemini.py",
    "gen_narration": HERE / "gen_narration_edge.py",
    "verify_narration": HERE / "verify_narration.py",
    "build_timeline": HERE / "build_timeline.py",
    "mix_audio": HERE / "mix_audio.py",
    "build_composition": HERE / "build_composition.py",
    "verify_output": HERE / "verify_output.py",
}


def slugify(text, max_len=40):
    """Converte o assunto/prompt em nome de diretorio seguro (sem acentos)."""
    if not text:
        return "projeto"
    slug = unicodedata.normalize("NFKD", text.lower().strip())
    slug = "".join(c for c in slug if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")[:max_len].strip("-")
    return slug or "projeto"


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- bancos locais ---
def extrair_palavras_chave(texto: str) -> list:
    """Extrai palavras importantes de uma descricao de cena/assunto."""
    texto = normalizar_texto_local(texto or "")
    stop = {"o","a","os","as","um","uma","de","do","da","dos","das","e","em","no","na",
            "nos","nas","por","para","com","sem","sobre","entre","que","quem","qual",
            "se","nao","ser","estar","tem","vai","foi","era","sera","ja","sao","esta",
            "estao","mais","menos","muito","bem","mal","sim"}
    palavras = re.findall(r"\w+", texto)
    return [p for p in palavras if p not in stop and len(p) > 2]


def normalizar_texto_local(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", t or "").encode("ascii","ignore").decode()
    return re.sub(r"\s+"," ",t).strip().lower()


def buscar_imagem_banco(descricao_cena: str, limite: int = 5) -> str | None:
    """Busca no indice_midia.db uma imagem adequada para a cena.
    Retorna caminho do JPG ou None."""
    if not DB_IMAGENS.exists() or abrir_db is None:
        return None
    try:
        db = abrir_db(str(DB_IMAGENS))
    except Exception:
        return None
    palavras = extrair_palavras_chave(descricao_cena)
    if not palavras:
        db.close()
        return None
    termos = [f'"{t}"' for t in palavras]
    consulta_and = " AND ".join(termos)
    consulta_or = " OR ".join(termos)
    resultados = []
    try:
        rows = db.execute(
            "SELECT caminho, descricao, palavras_chave, bm25(busca) AS r "
            "FROM busca WHERE busca MATCH ? ORDER BY r LIMIT ?",
            (consulta_and, limite * 2)).fetchall()
        for r in rows:
            resultados.append({"caminho": r[0], "descricao": r[1] or "",
                               "palavras_chave": r[2] or "", "score": r[3]})
    except Exception:
        pass
    if not resultados:
        try:
            rows = db.execute(
                "SELECT caminho, descricao, palavras_chave, bm25(busca) AS r "
                "FROM busca WHERE busca MATCH ? ORDER BY r LIMIT ?",
                (consulta_or, limite * 2)).fetchall()
            for r in rows:
                resultados.append({"caminho": r[0], "descricao": r[1] or "",
                                   "palavras_chave": r[2] or "", "score": r[3]})
        except Exception:
            pass
    db.close()
    validos = [r for r in resultados if Path(r["caminho"]).exists()]
    if not validos:
        return None
    validos.sort(key=lambda x: x["score"])
    return validos[0]["caminho"]


def listar_musicas_banco() -> list:
    """Lista trilhas de audio disponiveis no banco de musicas.

    Ignora arquivos de mix final (nao sao trilhas) e o proprio arquivo de
    controle. Retorna caminhos ordenados de forma estavel.
    """
    musicas = []
    if not BANCO_MUSICAS.exists():
        return musicas
    for ext in ("*.wav", "*.mp3", "*.m4a", "*.ogg", "*.flac", "*.wma"):
        musicas.extend(BANCO_MUSICAS.rglob(ext))
    filtradas = [
        p for p in musicas
        if not p.name.lower().startswith(("final_mix", "musicas_controle"))
    ]
    return [str(p) for p in sorted(set(filtradas))]


def carregar_controle_musicas() -> dict:
    """Le o controle de uso das trilhas do banco (cria vazio se ausente)."""
    if MUSICAS_CONTROLE.exists():
        try:
            dados = json.loads(MUSICAS_CONTROLE.read_text(encoding="utf-8"))
            if isinstance(dados, dict):
                dados.setdefault("usos", {})
                dados.setdefault("sequencia", [])
                return dados
        except Exception:
            pass
    return {"usos": {}, "sequencia": []}


def salvar_controle_musicas(ctrl: dict) -> None:
    """Persiste o controle de uso das trilhas do banco."""
    MUSICAS_CONTROLE.parent.mkdir(parents=True, exist_ok=True)
    MUSICAS_CONTROLE.write_text(
        json.dumps(ctrl, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def escolher_musica_banco(prompt_musica: str, slug: str | None = None) -> str | None:
    """Escolhe uma trilha do banco sem repetir entre projetos.

    Prefere trilhas nunca usadas; quando todas ja foram usadas, escolhe a de
    uso mais antigo (LRU). Registra o uso em musicas_controle.json.
    """
    musicas = listar_musicas_banco()
    if not musicas:
        return None

    ctrl = carregar_controle_musicas()
    usos = ctrl.setdefault("usos", {})
    sequencia = ctrl.setdefault("sequencia", [])
    ordem_atual = len(sequencia)

    livres = [m for m in musicas if not usos.get(Path(m).name, {}).get("slugs")]
    if livres:
        import random
        random.seed(hash(prompt_musica) & 0xffffffff)
        escolhida = random.choice(livres)
    else:
        escolhida = min(
            musicas,
            key=lambda m: usos.get(Path(m).name, {}).get("ultimo_uso", 0),
        )

    nome = Path(escolhida).name
    entrada = usos.setdefault(nome, {"slugs": [], "ultimo_uso": 0})
    if slug and slug not in entrada["slugs"]:
        entrada["slugs"].append(slug)
    if slug not in [item.get("slug") for item in sequencia[-1:]]:
        ordem_atual += 1
        entrada["ultimo_uso"] = ordem_atual
        sequencia.append({"musica": nome, "slug": slug, "ordem": ordem_atual})
        salvar_controle_musicas(ctrl)

    return escolhida


def copiar_para_projeto(origem: Path, destino_dir: Path, nome: str) -> Path:
    """Copia arquivo para o diretório de destino do projeto."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    dst = destino_dir / nome
    if origem.resolve() == dst.resolve():
        return dst
    shutil.copyfile(origem, dst)
    return dst


# ---------------------------------------------------------------- estado ---
def run(cmd, label=""):
    print(f"== {label or ' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        msg = label or " ".join(cmd)
        raise RuntimeError(f"{msg} (exit {r.returncode})")
    return r


# ---------------------------------------------------------------- estado ---

class Project:
    """Estado do projeto: caminhos + checkpoints (project.json)."""

    def __init__(self, slug, prompt=None):
        self.slug = slug
        self.prompt = prompt
        self.dir = ROOT / "projects" / slug
        self.artifacts = self.dir / "artifacts"
        self.scenes_dir = self.dir / "scenes"
        self.images_src = self.dir / "assets" / "images" / "gemini" / "scenes"
        self.narration_dir = self.dir / "assets" / "audio" / "narration"
        self.audio_dir = self.dir / "assets" / "audio"
        self.output_dir = self.dir / "output"

        self.script = self.artifacts / "script.json"
        self.scenes_json = self.artifacts / "scenes.json"
        self.image_prompts = self.artifacts / "image_prompts.json"
        self.narration_timing = self.artifacts / "narration_timing.json"
        self.timeline_json = self.artifacts / "timeline.json"
        self.bgm = self.audio_dir / "gemini" / "bgm_gemini.wav"
        self.bgm_proc = self.audio_dir / "music" / "bgm_procedural.wav"
        self.narration_full = self.audio_dir / "narration_full.wav"
        self.final_mix = self.audio_dir / "final_mix.m4a"
        self.composition = self.dir / "composition.html"
        self.video = self.output_dir / f"{slug}.mp4"
        self.state_file = self.dir / "project.json"

        self.state = self._load_state()

    # ---------- estado ----------
    def _load_state(self):
        if self.state_file.exists():
            try:
                return load_json(self.state_file)
            except Exception:
                pass
        st = {"slug": self.slug, "prompt": self.prompt, "phases": {}, "history": []}
        return st

    def save_state(self):
        st = self.state
        st.setdefault("phases", {})
        st.setdefault("history", [])
        if self.prompt:
            st["prompt"] = self.prompt
        save_json(self.state_file, st)

    def mark(self, phase, ok=True, detail=""):
        st = self.state
        st["phases"][phase] = {"done": bool(ok), "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                               "detail": detail}
        if ok:
            st["history"].append({"ts": st["phases"][phase]["ts"], "phase": phase,
                                  "event": "done", "detail": detail[:200]})
        self.save_state()

    def reset_phase(self, phase):
        self.state.setdefault("phases", {}).pop(phase, None)
        self.save_state()

    def is_done(self, phase, force=False):
        if force:
            return False
        rec = self.state.get("phases", {}).get(phase)
        return bool(rec and rec.get("done"))

    def validate_file_phase(self, phase):
        """Validacao fisica extra: arquivos existem / JSON valido / contagem."""
        try:
            if phase == "script":
                d = load_json(self.script)
                assert d.get("title") and len(d.get("sections", [])) >= 4
                problemas = validate_contract(d)
                assert not problemas, "contrato de narracao: " + "; ".join(problemas)
            elif phase == "scenes":
                d = load_json(self.scenes_json)
                p = load_json(self.image_prompts)
                ids = [k for k in d if not str(k).startswith("_")]
                assert ids and all((self.scenes_dir / f"{i}.html").exists() for i in ids)
                assert len(p) >= len(ids)
            elif phase == "images":
                prompts = load_json(self.image_prompts)
                missing = [n for n in prompts if not (self.images_src / f"{n}.jpg").exists()]
                assert not missing, f"faltam imagens: {missing}"
            elif phase == "music":
                src = self.bgm if self.bgm.exists() else self.bgm_proc
                assert src.exists() and src.stat().st_size > 100000, "trilha ausente (gemini e procedural)"
            elif phase == "narration":
                d = load_json(self.narration_timing)
                assert d and all(Path(r["path"]).exists() for r in d)
            elif phase == "timeline":
                d = load_json(self.timeline_json)
                assert d.get("timeline") and d.get("total", 0) > 5
                assert self.narration_full.exists()
            elif phase == "mix":
                assert self.final_mix.exists() and self.final_mix.stat().st_size > 100000
            elif phase == "compose":
                assert self.composition.exists() and self.composition.stat().st_size > 5000
            elif phase == "preprocess":
                prompts = load_json(self.image_prompts)
                dst = HF_DIR / "assets" / "images"
                missing = [n for n in prompts if not (dst / f"{n}.jpg").exists()]
                assert not missing, f"faltam no HyperFrames: {missing}"
            elif phase == "render":
                assert self.video.exists() and self.video.stat().st_size > 100000
        except AssertionError as e:
            return str(e)
        except FileNotFoundError:
            return "arquivo ausente"
        except Exception as e:
            return f"invalido: {e}"
        return None  # ok

    def checkpoint(self, phase, force=False):
        """True = pode pular (checkpoint valido). False = precisa rodar."""
        if self.is_done(phase, force=force):
            err = self.validate_file_phase(phase)
            if err is None:
                print(f"== CHECKPOINT {phase}: feito em {self.state['phases'][phase]['ts']} -> pulando")
                return True
            print(f"== CHECKPOINT {phase}: invalido ({err}) -> vai refazer")
        return False

    def ensure_dirs(self):
        for d in (self.dir, self.artifacts, self.scenes_dir, self.images_src,
                  self.narration_dir, self.audio_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)

    def tree(self):
        print(f"\n== Projeto: {self.dir}")
        for p in (self.script, self.scenes_json, self.image_prompts,
                  self.narration_timing, self.timeline_json, self.bgm,
                  self.narration_full, self.final_mix, self.composition,
                  self.output_dir, self.video, self.state_file):
            print(f"    {p}")
        print()


# ---------------------------------------------------------------- fases ----

def phase_script(args, p: Project):
    run([sys.executable, str(SCRIPTS["script_from_prompt"]),
         "--prompt", args.prompt or p.prompt or p.slug,
         "--out", str(p.script)],
        "FASE script: roteiro via Gemini WEB (Chrome, conta gratuita)")
    p.mark("script", detail=str(p.script))


def phase_scenes(args, p: Project):
    run([sys.executable, str(SCRIPTS["scenes_from_script"]),
         "--script", str(p.script),
         "--scenes-out", str(p.scenes_json),
         "--prompts-out", str(p.image_prompts)],
        "FASE scenes: cenas + prompts (local deterministico)")
    run([sys.executable, str(SCRIPTS["scene_htmls"]),
         "--script", str(p.script),
         "--scenes", str(p.scenes_json),
         "--out-dir", str(p.scenes_dir)],
        "FASE scenes: overlays HTML (local deterministico)")
    p.mark("scenes", detail=f"{p.scenes_json}")


def phase_images(args, p: Project):
    """Gera imagens uma por uma com loop de quarentena (ate 4 tentativas).
    Antes de gerar via Gemini, verifica se existe imagem adequada no banco
    local (banco de imagens / indice_midia.db). Se achar, copia para o
    projeto e pula a geracao."""
    prompts = load_json(p.image_prompts)
    # ids de imagem = chaves do image_prompts.json (sem o _help)
    image_ids = [k for k in prompts.keys() if not k.startswith("_")]
    out_dir = p.dir / "assets" / "images" / "gemini" / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"== FASE images: {len(image_ids)} imagem(ns) (banco local primeiro, Gemini se nao achar)", flush=True)

    def tentar(nome: str, idx=None) -> bool:
        """Tenta gerar/obter UNA imagem. Retorna True se sucesso (arquivo > 0 bytes).
        Pula se o arquivo ja existe e nao esta vazio (evita re-gerar tudo em retomada)."""
        jpg = out_dir / (nome + ".jpg")
        if jpg.exists() and jpg.stat().st_size > 0:
            if idx:
                print(f"== IMAGEM {idx}/{len(image_ids)}: {nome} (ja existe)", flush=True)
            print(f"  [{nome}] OK (ja existe)", flush=True)
            return True
        if idx:
            print(f"== IMAGEM {idx}/{len(image_ids)}: {nome}", flush=True)

        # 1) Tenta encontrar imagem adequada no banco local por descricao da cena
        prompt_texto = prompts.get(nome, "")
        desc_busca = prompt_texto
        # Tira prefixos comuns do prompt para deixar mais limpo a busca
        for prefixo in ("CENA (gere exatamente esta cena): ", "CENA: "):
            if desc_busca.startswith(prefixo):
                desc_busca = desc_busca[len(prefixo):]
                break
        caminho_banco = buscar_imagem_banco(desc_busca, limite=5)
        if caminho_banco:
            try:
                copiar_para_projeto(Path(caminho_banco), out_dir, nome + ".jpg")
                print(f"  [{nome}] OK (banco local: {Path(caminho_banco).name})", flush=True)
                return True
            except Exception as e:
                print(f"  [{nome}] falhou ao copiar do banco ({e}), tenta Gemini", flush=True)

        # 2) Nao achou no banco: gera via Gemini
        rc, name, size = run_single_fetch(nome, out_dir, args)
        ok = rc == 0 and size > 0
        status = "OK" if ok else f"FALHA (rc={rc} bytes={size})"
        print(f"  [{name}] {status}", flush=True)
        return ok

    def run_single_fetch(nome: str, out_dir: Path, args) -> tuple:
        """Chama fetch_images.py --single para uma imagem (stdout ao vivo)."""
        cmd = [sys.executable, str(SCRIPTS["fetch_images"]),
               "--proj", str(p.dir),
               "--single", nome,
               "--wait", str(args.wait),
               "--pause", str(args.pause)]
        r = subprocess.run(cmd)
        # arquivo gerado?
        jpg = out_dir / (nome + ".jpg")
        size = jpg.stat().st_size if jpg.exists() else 0
        return r.returncode, nome, size

    # primeira passagem: todas as imagens
    quarantine = []
    for i, nome in enumerate(image_ids, 1):
        if not tentar(nome, idx=i):
            quarantine.append(nome)

    # loops de quarentena: ate 4 tentativas
    tentativa = 1
    while quarantine and tentativa <= 4:
        print(f"== QUARENTENA loop {tentativa}/4: {len(quarantine)} imagem(ns) pendente(s)", flush=True)
        ainda_falham = []
        for nome in quarantine:
            if not tentar(nome):
                ainda_falham.append(nome)
        quarantine = ainda_falham
        tentativa += 1

    if quarantine:
        print(f"== ERRO: {len(quarantine)} imagem(ns) falharam apos 4 loops de quarentena:")
        for nome in quarantine:
            print(f"   - {nome}")
        raise RuntimeError(f"imagens em quarentena falharam: {quarantine}")

    sucesso = len(image_ids) - len(quarantine)
    p.mark("images", detail=f"{sucesso}/{len(image_ids)} imagens geradas")


def _music_prompt(p: Project, args) -> str:
    """Prompt da trilha derivado do assunto/prompt do projeto (nada fixo)."""
    topic = getattr(args, "prompt", None) or p.prompt or p.slug
    title = ""
    try:
        title = load_json(p.script).get("title", "")
    except Exception:
        pass
    tema = title or topic
    return ("Crie uma musica instrumental para o video '%s' (%s). "
            "Estilo trilha de desenho animado moderno: ukulele, pizzicato de "
            "cordas, marimba e assobio; ritmo alegre e leve, ~110 BPM; clima "
            "engracado e carinhoso; sem vocais e sem letra; duracao ~3 minutos."
            % (tema, topic))


def phase_music(args, p: Project):
    prompt = _music_prompt(p, args)
    p.dir.mkdir(parents=True, exist_ok=True)
    p.audio_dir.mkdir(parents=True, exist_ok=True)

    # 1) Verifica banco de músicas local antes de gerar via Gemini.
    # Preferência: usar o banco quando houver acervo mínimo. Se o acervo ainda
    # for pequeno, usa mesmo assim desde que exista trilha ainda não usada
    # (rotação sem repetição); só gera via Gemini quando não há trilha livre.
    musicas_banco = listar_musicas_banco()
    if len(musicas_banco) >= MIN_MUSICAS_BANCO:
        musica_banco = escolher_musica_banco(prompt, p.slug)
    else:
        ctrl = carregar_controle_musicas()
        usos = ctrl.get("usos", {})
        livres = [
            m for m in musicas_banco
            if not usos.get(Path(m).name, {}).get("slugs")
        ]
        if livres:
            musica_banco = escolher_musica_banco(prompt, p.slug)
            print(f"== FASE music: banco com {len(musicas_banco)} trilha(s), "
                  f"{len(livres)} livre(s); usando rotação local", flush=True)
        else:
            musica_banco = None
            print(f"== FASE music: banco com {len(musicas_banco)} trilha(s), "
                  f"todas usadas; gera via Gemini", flush=True)
    if musica_banco:
        try:
            origem = Path(musica_banco)
            destino = copiar_para_projeto(
                origem, p.audio_dir, f"{p.slug}_musica{origem.suffix}"
            )
            print(f"== FASE music: trilha do banco local (destino: {destino})", flush=True)
            # Garante que bgm/apontamentos do projeto existam
            if p.bgm.exists():
                p.bgm.unlink()
            p.bgm.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(destino, p.bgm)
            p.mark("music", detail=str(p.bgm))
            return
        except Exception as e:
            print(f"== FASE music: falhou ao copiar do banco ({e}), gera via Gemini", flush=True)

    # 2) Gera via Gemini
    attempts = 2
    for i in range(1, attempts + 1):
        try:
            run([sys.executable, str(SCRIPTS["fetch_music"]),
                 "--proj", str(p.dir),
                 "--prompt", prompt,
                 "--wait", str(args.wait)],
                "FASE music: trilha via Gemini WEB (Chrome, conta gratuita)"
                + (f" (tentativa {i})" if i > 1 else ""))
            break
        except RuntimeError:
            if i == attempts:
                if args.provider == "procedural":
                    print("== trilha web falhou; gerando trilha procedural local")
                    run([sys.executable, str(HERE / "gen_music_procedural.py"),
                         "--proj", str(p.dir)], "FASE music: procedural (local)")
                    break
                raise
            print("== nova tentativa de trilha em 10s...")
            time.sleep(10)
    if not (p.bgm.exists() and p.bgm.stat().st_size > 100000):
        # provider procedural escreve em assets/audio/music
        if not p.bgm_proc.exists():
            raise RuntimeError("trilha ausente apos fase music")
    p.mark("music", detail=str(p.bgm if p.bgm.exists() else p.bgm_proc))


VOICE_STATE = HERE / ".narration_voice_state.json"


def _pick_gemini_voice(cfg):
    """Escolhe a proxima voz Gemini da lista (alternancia entre videos)."""
    tts = cfg.get("tts", {})
    voices = tts.get("gemini_voices") or [tts.get("voice", "Leda")]
    if not tts.get("alternate_voices", True) or len(voices) < 2:
        return voices[0]
    state = {}
    if VOICE_STATE.exists():
        try:
            state = json.loads(VOICE_STATE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    idx = int(state.get("index", -1)) + 1
    if idx >= len(voices):
        idx = 0
    voice = voices[idx]
    VOICE_STATE.write_text(json.dumps({"index": idx, "last": voice}, ensure_ascii=False),
                           encoding="utf-8")
    return voice


def phase_narration(args, p: Project):
    cfg = load_json(HERE / "config.json")
    tts = cfg.get("tts", {})
    provider = (getattr(args, "narration_provider", None) or tts.get("provider") or "edge").lower()
    if provider not in ("edge", "gemini"):
        provider = "edge"

    voice_arg = (getattr(args, "voice", "") or "").strip()
    edge_style = (not voice_arg) or voice_arg.lower().startswith("pt-br-") \
        or voice_arg.lower().endswith("neural")

    def _run_edge(voice, rate, pitch, style, workers, label):
        run([sys.executable, str(SCRIPTS["gen_narration"]),
             "--proj", str(p.dir),
             "--voice", voice,
             "--rate", rate,
             "--pitch", pitch,
             "--style", style,
             "--workers", str(workers)], label)
        p.state.setdefault("narration", {}).update({"provider": "edge", "voice": voice})
        p.save_state()

    if provider == "gemini":
        voice = _pick_gemini_voice(cfg) if edge_style else voice_arg
        model = tts.get("model", "gemini-3.8-flash-tts")
        cmd = [sys.executable, str(HERE / "gen_narration_gemini_sections.py"),
               "--proj", str(p.dir),
               "--voice", voice,
               "--model", model]
        if getattr(args, "force", False):
            cmd.append("--force")
        try:
            run(cmd, "FASE narration: Gemini TTS '%s' (Google AI Studio)" % voice)
            p.state.setdefault("narration", {}).update({"provider": "gemini", "voice": voice})
            p.save_state()
        except RuntimeError as e:
            if not tts.get("edge_fallback", True):
                raise
            edge_voice = cfg.get("voice", "pt-BR-ThalitaNeural")
            print("== FALLBACK: Gemini TTS indisponivel (%s)." % str(e).splitlines()[0][:120])
            print("== FALLBACK: gerando narracao com Edge-TTS '%s' (local, sem API)." % edge_voice)
            _run_edge(edge_voice,
                      cfg.get("voice_rate", "+12%"),
                      cfg.get("voice_pitch", "+8Hz"),
                      "excited",
                      getattr(args, "workers", 4),
                      "FASE narration: FALLBACK Edge-TTS (local, sem API)")
            p.state["narration"]["fallback_from"] = "gemini"
            p.save_state()
    else:
        _run_edge(args.voice, args.rate, args.pitch, args.style, args.workers,
                  "FASE narration: narracao Edge-TTS (local, sem API)")
    p.mark("narration", detail=str(p.narration_timing))


def phase_timeline(args, p: Project):
    run([sys.executable, str(SCRIPTS["build_timeline"]),
         "--proj", str(p.dir)],
        "FASE timeline: linha do tempo (local)")
    p.mark("timeline", detail=str(p.timeline_json))


def phase_mix(args, p: Project):
    cmd = [sys.executable, str(SCRIPTS["mix_audio"]),
           "--proj", str(p.dir),
           "--hf-dir", str(HF_DIR)]
    if args.provider:
        cmd += ["--provider", args.provider]
    if args.gain is not None:
        cmd += ["--gain", str(args.gain)]
    run(cmd, "FASE mix: narracao + trilha (local)")
    p.mark("mix", detail=str(p.final_mix))


def phase_compose(args, p: Project):
    run([sys.executable, str(SCRIPTS["build_composition"]),
         "--timeline", str(p.timeline_json),
         "--scenes", str(p.scenes_json),
         "--scenes-dir", str(p.scenes_dir),
         "--proj", str(p.dir),
         "--out", str(p.composition)],
        "FASE compose: composicao HyperFrames (local)")
    p.mark("compose", detail=str(p.composition))


def phase_preprocess(args, p: Project):
    run([sys.executable, str(SCRIPTS["preprocess_images"]),
         "--proj", str(p.dir),
         "--scenes", str(p.scenes_json),
         "--hf-dir", str(HF_DIR)],
        "FASE preprocess: imagens para o HyperFrames (local)")
    p.mark("preprocess", detail="copiado para " + str(HF_DIR / "assets" / "images"))


def phase_render(args, p: Project):
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File",
         str(HERE / "render.ps1"),
         "-ProjectDir", str(p.dir),
         "-Slug", p.slug,
         "-CompFile", str(p.composition),
         "-MixFile", str(p.final_mix)]
    if getattr(args, "skip_check", False):
        cmd.append("-SkipCheck")
    run(cmd, "FASE render: renderizando video (HyperFrames)")
    p.mark("render", detail=str(p.video))
    try:
        run([sys.executable, str(SCRIPTS["verify_output"]),
             "--proj", str(p.dir),
             "--file", str(p.video)], "FASE render: verificando saida")
    except RuntimeError as e:
        print(f"AVISO: verificacao reportou problema (video existe): {e}")


def phase_youtube(args, p: Project):
    """Fase youtube: publica no YouTube com descricao, thumbnail e privacidade publica."""
    print("== FASE youtube: iniciando", flush=True)
    if not p.video.exists():
        print("== YOUTUBE: video ausente, nada para publicar", flush=True)
        args.publish_ok = False
        return False
    title = (getattr(args, "yt_title", "") or "").strip()
    if not title:
        try:
            title = load_json(p.script).get("title", "")
        except Exception:
            title = ""
    if not title:
        title = p.prompt or p.slug

    # Descricao completa: conteudo, marcacao de IA, sem promocao paga, idioma
    auto_desc = (
        f"{title}\n\n"
        f"{p.prompt or title}\n\n"
        "Vídeo gerado por inteligência artificial (IA).\n"
        "Não contém promoção paga.\n"
        "Idioma da narração e das legendas: Português do Brasil.\n"
        "Conteúdo infantil (feito para crianças).\n\n"
        "#cachorro #animacao #infantil #frida #luna #desenhoanimado"
    )
    desc = getattr(args, "yt_desc", "") or auto_desc
    tags = getattr(args, "yt_tags", "") or "cachorro,animacao,infantil"
    privacy = getattr(args, "privacy", "public")
    category = "24"
    made_for_kids = bool(getattr(args, "yt_kids", True)) and not getattr(args, "nao_kids", False)
    default_language = getattr(args, "default_language", "pt-BR") or "pt-BR"
    default_audio_language = getattr(args, "default_audio_language", "pt-BR") or "pt-BR"
    # Thumbnail: usa --yt-thumb se informado, senao busca primeira imagem do projeto
    thumb = getattr(args, "yt_thumb", "") or ""
    if not thumb:
        # tenta encontrar primeira imagem de cena disponível
        img_dir = p.dir / "assets" / "images" / "gemini" / "scenes"
        if img_dir.exists():
            imgs = sorted(img_dir.glob("*.jpg"))
            if imgs:
                thumb = str(imgs[0])
    secret = getattr(args, "yt_secret", "") or ""

    cmd = [
        sys.executable, str(HERE / "youtube_upload.py"),
        "--video", str(p.video),
        "--title", title,
        "--description", desc,
        "--tags", tags,
        "--privacy", privacy,
        "--category", category,
        "--default-language", default_language,
        "--default-audio-language", default_audio_language,
        "--client-secret", secret or str(HERE / "client_secret.json"),
    ]
    if made_for_kids:
        cmd.append("--made-for-kids")
    if thumb:
        cmd += ["--thumbnail", thumb]
        print(f"== YOUTUBE: thumbnail={thumb}", flush=True)
    else:
        print("== YOUTUBE: AVISO - nenhuma thumbnail encontrada", flush=True)

    print(f"== YOUTUBE: publicando '{title[:80]}' (privacidade={privacy}, kids={made_for_kids}, lang={default_language})", flush=True)
    r = subprocess.run(cmd)
    ok = r.returncode == 0
    args.publish_ok = ok
    if ok:
        print("== YOUTUBE: PUBLICADO COM SUCESSO", flush=True)
    else:
        print(f"== YOUTUBE: FALHOU codigo {r.returncode}", flush=True)
    return ok


PHASE_FN = {
    "script": phase_script,
    "scenes": phase_scenes,
    "images": phase_images,
    "music": phase_music,
    "narration": phase_narration,
    "timeline": phase_timeline,
    "mix": phase_mix,
    "compose": phase_compose,
    "preprocess": phase_preprocess,
    "render": phase_render,
    "youtube": phase_youtube,
}

# Grafo de dependencias: quando uma fase e refeita, as descendentes vao caducar.
DEPS = {
    "script": ["scenes", "narration", "timeline"],
    "scenes": ["preprocess", "compose"],
    "images": ["preprocess"],
    "music": ["mix"],
    "narration": ["timeline"],
    "timeline": ["mix", "compose"],
    "mix": ["render"],
    "compose": ["render"],
    "preprocess": ["render"],
    "render": [],
}


def invalidate_downstream(p: Project, phase):
    """Marca fases dependentes como pendentes (o conteudo fisico permanece,
    mas os checkpoints deixam de valer ate serem refeito em cima da nova fase)."""
    def walk(node):
        for child in DEPS.get(node, []):
            rec = p.state.get("phases", {}).get(child)
            if rec and rec.get("done"):
                p.reset_phase(child)
                print(f"== CADUCADO: {child} depende de {phase} novo -> sera refeito")
            walk(child)
    walk(phase)


# ------------------------------------------------------------ execucao -----

def _validate_prereq(p: Project, phase, missing_ok=None):
    """Avisa (nao para) se um prerequisito fisico de fase anterior esta ausente."""
    deps = {
        "scenes": ["script"],
        "images": ["scenes"],
        "narration": ["script"],
        "timeline": ["narration"],
        "mix": ["timeline", "music_src"],
        "compose": ["scenes", "timeline"],
        "preprocess": ["images", "scenes"],
        "render": ["compose", "mix", "preprocess"],
    }
    checks = {
        "script": p.script, "scenes": p.scenes_json, "images": None,
        "music_src": None, "narration": p.narration_timing,
        "timeline": p.timeline_json, "mix": p.final_mix,
        "compose": p.composition,
    }
    need = deps.get(phase, [])
    for n in need:
        if n not in checks or checks[n] is None:
            continue
        if not checks[n].exists():
            print(f"AVISO: prerequisito fisico de {phase} ausente: {checks[n]} (fase {n})")


def execute_phases(args, p: Project, phases_to_run, force=False):
    run_parallel = not getattr(args, "no_parallel", False)
    only = set(phases_to_run)

    # phases extras que nao estao na lista PHASES (ex: youtube)
    extra_phases = only - set(PHASES)

    # Quando music e images estao juntos no plano, executa MUSIC primeiro
    # (sequencial) para nao haver conflito de Chrome/gemini_fetch entre
    # geracao de trilha e geracao de imagens.
    music_needs_first = (
        run_parallel
        and "music" in only
        and "images" in only
        and not p.checkpoint("music", force)
    )
    if music_needs_first:
        print("== MUSIC PRIMEIRO (antes de imagens) para evitar conflito de Chrome", flush=True)
        print("== FASE music: iniciando", flush=True)
        PHASE_FN["music"](args, p)
        invalidate_downstream(p, "music")
        only.discard("music")  # ja rodou, nao repete no loop

    music_thread = None
    ex = ThreadPoolExecutor(max_workers=1) if run_parallel else None
    try:
        # music pode ainda rodar em paralelo com script/scenes (sem images)
        music_first = {"music", "script", "scenes"}
        if run_parallel and only & music_first \
           and not p.checkpoint("music", force):
            print("== FASE music: iniciando (paralelo)", flush=True)
            music_thread = ex.submit(PHASE_FN["music"], args, p)

        for phase in PHASES:
            if phase not in only:
                continue
            if phase == "music" and music_thread:
                music_thread.result()  # aguarda a thread lancada antes
                invalidate_downstream(p, "music")
                music_thread = None
                continue
            if p.checkpoint(phase, force):
                continue
            _validate_prereq(p, phase)
            print(f"== FASE {phase}: iniciando", flush=True)
            PHASE_FN[phase](args, p)
            invalidate_downstream(p, phase)

        # executa fases extras (ex: youtube) que nao estao em PHASES
        for phase in sorted(extra_phases):
            if phase not in only:
                continue
            if phase not in PHASE_FN:
                print(f"AVISO: fase '{phase}' nao tem implementacao, pulando")
                continue
            if p.checkpoint(phase, force):
                continue
            print(f"== FASE {phase}: iniciando", flush=True)
            PHASE_FN[phase](args, p)
            invalidate_downstream(p, phase)
    finally:
        if music_thread:
            music_thread.result()
        if ex:
            ex.shutdown(wait=True)


def get_project(args):
    if getattr(args, "slug", None):
        return Project(args.slug, getattr(args, "prompt", None))
    if getattr(args, "prompt", None):
        return Project(slugify(args.prompt), args.prompt)
    raise SystemExit("ERRO: informe --prompt ou --slug (veja python scripts/pipeline.py status)")

def load_topics_queue():
    """Lê scripts/topics.txt e retorna tópicos válidos (sem # e linhas vazias)."""
    topics_file = HERE / "topics.txt"
    if not topics_file.exists():
        return []
    topics = []
    for line in topics_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        topics.append(line)
    return topics


def find_duplicate_project(prompt):
    """Verifica se já existe um projeto com o mesmo prompt (consulta o JSON de
    entregas, não varre pastas de projetos)."""
    return find_duplicate_by_prompt(prompt)


def next_topic_in_queue(current_prompt):
    """Retorna o próximo tópico da fila de topics.txt que ainda não virou projeto."""
    topics = load_topics_queue()
    if not topics:
        return None
    processed = set()
    projects_dir = ROOT / "projects"
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir():
                processed.add(slugify(d.name))
    current_slug = slugify(current_prompt)
    for t in topics:
        ts = slugify(t)
        if ts != current_slug and ts not in processed:
            return t
    return None


def publish_to_youtube(p: Project, args):
    """Fase publish: envia o MP4 para o YouTube (youtube_upload.py)."""
    print("== FASE publish: iniciando", flush=True)
    if not p.video.exists():
        print("== YOUTUBE: video ausente, nada para publicar", flush=True)
        return
    title = (getattr(args, "yt_title", "") or "").strip()
    if not title:
        try:
            title = load_json(p.script).get("title", "")
        except Exception:
            title = ""
    if not title:
        title = p.prompt or p.slug

    auto_desc = (
        f"{title}\n\n"
        f"{p.prompt or title}\n\n"
        "Vídeo gerado por inteligência artificial (IA).\n"
        "Não contém promoção paga.\n"
        "Idioma da narração e das legendas: Português do Brasil.\n"
        "Conteúdo infantil (feito para crianças).\n\n"
        "#cachorro #animacao #infantil #frida #luna #desenhoanimado"
    )
    desc = p.yt_desc if hasattr(args, "yt_desc") and args.yt_desc else auto_desc
    desc = getattr(args, "yt_desc", "") or auto_desc
    tags = getattr(args, "yt_tags", "") or "cachorro,animação"
    privacy = getattr(args, "privacy", "private")
    default_language = getattr(args, "default_language", "pt-BR") or "pt-BR"
    default_audio_language = getattr(args, "default_audio_language", "pt-BR") or "pt-BR"
    cmd = [
        sys.executable, str(HERE / "youtube_upload.py"),
        "--video", str(p.video),
        "--title", title,
        "--description", desc,
        "--tags", tags,
        "--privacy", privacy,
        "--category", "24",
        "--default-language", default_language,
        "--default-audio-language", default_audio_language,
    ]
    if getattr(args, "yt_kids", False):
        cmd.append("--made-for-kids")
    print(f"== YOUTUBE: publicando '{title[:80]}' (privacidade={privacy}, lang={default_language})", flush=True)
    r = subprocess.run(cmd)
    if r.returncode == 0:
        print("== YOUTUBE: PUBLICADO COM SUCESSO", flush=True)
    else:
        print(f"== YOUTUBE: FALHOU codigo {r.returncode} — publique manualmente em Publicar", flush=True)


def update_youtube_metadata(p: Project, args):
    """Atualiza metadados (titulo, descricao, tags, thumbnail) de um video ja enviado ao YouTube."""
    print("== FASE yt-meta: atualizando metadados do YouTube", flush=True)
    video_id = getattr(args, "yt_video_id", "") or ""
    if not video_id:
        print("== YT-META: nenhum --yt-video-id informado, pulando atualizacao de metadados.", flush=True)
        return

    title = (getattr(args, "yt_title", "") or "").strip()
    if not title:
        try:
            title = load_json(p.script).get("title", "")
        except Exception:
            title = ""
    if not title:
        title = p.prompt or p.slug

    desc = getattr(args, "yt_desc", "") or ""
    if not desc:
        desc = p.prompt or title

    tags = getattr(args, "yt_tags", "") or "cachorro,animacao"
    privacy = getattr(args, "privacy", "public")
    category = "24"
    made_for_kids = bool(getattr(args, "yt_kids", True)) and not getattr(args, "nao_kids", False)
    thumb = getattr(args, "yt_thumb", "") or ""
    if not thumb:
        img_dir = p.dir / "assets" / "images" / "gemini" / "scenes"
        if img_dir.exists():
            imgs = sorted(img_dir.glob("*.jpg"))
            if imgs:
                thumb = str(imgs[0])
    secret = getattr(args, "yt_secret", "") or ""

    cmd = [
        sys.executable, str(HERE / "youtube_update.py"),
        "--video-id", video_id,
        "--title", title,
        "--description", desc,
        "--tags", tags,
        "--category", category,
        "--client-secret", secret or str(HERE / "client_secret.json"),
    ]
    if thumb:
        cmd += ["--thumbnail", thumb]
    if made_for_kids:
        cmd += ["--made-for-kids"]

    print(f"== YT-META: atualizando video '{title[:80]}' (id={video_id})", flush=True)
    try:
        subprocess.run(cmd, check=True)
        print("== YT-META: METADADOS ATUALIZADOS COM SUCESSO", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"== YT-META: FALHOU codigo {e.returncode}", flush=True)
        print("== Para atualizar depois: python scripts/youtube_update.py --video-id <ID> ...", flush=True)


def write_control_json(p: Project, args, t0: float, elapsed: float, publish_result=None):
    """Gera um JSON de controle/observabilidade com tudo sobre o projeto concluido.
    Serve de historico e permite retomar qualquer projeto ou cena depois."""
    try:
        import subprocess
        duration_s = None
        try:
            out = subprocess.run(
                [str(Path(cfg_ffmpeg_dir()) / "ffprobe.exe"), "-v", "error",
                 "-show_entries", "format=duration,size", "-of", "json", str(p.video)],
                capture_output=True, text=True)
            import json as _json
            d = _json.loads(out.stdout)
            for s in d.get("streams", []):
                if s.get("codec_type") == "video":
                    duration_s = float(d.get("format", {}).get("duration"))
                    break
        except Exception:
            pass

        # Resumo das fases
        phases_summary = {}
        for ph in PHASES:
            rec = p.state.get("phases", {}).get(ph)
            if rec:
                phases_summary[ph] = {
                    "done": rec.get("done"),
                    "ts": rec.get("ts"),
                    "detail": rec.get("detail", ""),
                }

        # Artefatos existentes
        def exists(path):
            try:
                return Path(path).exists()
            except Exception:
                return False

        control = {
            "slug": p.slug,
            "prompt": p.prompt,
            "status": "completed",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(elapsed, 2),
            "project_dir": str(p.dir),
            "output_dir": str(p.output_dir),
            "video": {
                "path": str(p.video),
                "exists": p.video.exists(),
                "size_bytes": p.video.stat().st_size if p.video.exists() else 0,
                "duration_s": duration_s,
            },
            "script": p.script.exists(),
            "scenes": p.scenes_json.exists(),
            "image_prompts": p.image_prompts.exists(),
            "narration_timing": p.narration_timing.exists(),
            "timeline": p.timeline_json.exists(),
            "bgm": p.bgm.exists(),
            "narration_full": p.narration_full.exists(),
            "final_mix": p.final_mix.exists(),
            "composition": p.composition.exists(),
            "phases": phases_summary,
            "publish": {
                "done": bool(getattr(args, "publish", False)) and bool(publish_result),
                "privacy": getattr(args, "privacy", None),
                "title": getattr(args, "yt_title", "") or "",
                "description": getattr(args, "yt_desc", "") or "",
            },
            "artifacts_dir": str(p.artifacts),
            "scenes_dir": str(p.scenes_dir),
            "images_dir": str(p.images_src),
            "narration_dir": str(p.narration_dir),
        }
        out_path = p.dir / "project-control.json"
        save_json(out_path, control)
        print(f"== CONTROLE: gravado em {out_path}", flush=True)
        return control
    except Exception as e:
        print(f"== CONTROLE: falha ao gravar JSON ({e})", flush=True)
        return None


def cfg_ffmpeg_dir():
    try:
        import json as _json
        cfg = _json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        return cfg.get("ffmpeg_dir", str(HERE.parent / "ffmpeg" / "bin"))
    except Exception:
        return str(HERE.parent / "ffmpeg" / "bin")

DELIVERIES_FILE = ROOT / "projects-deliveries.json"


def load_deliveries():
    """Carrega a lista de projetos ja entregues (para nao varrer pastas)."""
    if not DELIVERIES_FILE.exists():
        return {"delivered": []}
    try:
        return load_json(DELIVERIES_FILE)
    except Exception:
        return {"delivered": []}


def save_deliveries(data):
    DELIVERIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    save_json(DELIVERIES_FILE, data)


def record_delivery(p: Project, args, t0: float, elapsed: float, publish_result=None):
    """Registra a entrega de um projeto no JSON global de entregas.

    Contrato: so registra se o MP4 final existe e nao esta vazio. Sem isso, o
    tema seria marcado como entregue e nunca mais gerado (video fantasma).
    """
    if not (p.video.exists() and p.video.stat().st_size > 0):
        print(f"== ENTREGA: NAO registrada (video final ausente): {p.slug}", flush=True)
        return None
    data = load_deliveries()
    slug = p.slug
    data["delivered"] = [d for d in data["delivered"] if d.get("slug") != slug]

    delivery = {
        "slug": slug,
        "prompt": p.prompt,
        "status": "completed",
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(elapsed, 2),
        "project_dir": str(p.dir),
        "video_path": str(p.video),
        "video_exists": p.video.exists(),
        "video_size_bytes": p.video.stat().st_size if p.video.exists() else 0,
        "publish": {
            "done": bool(getattr(args, "publish", False)) and bool(publish_result),
            "privacy": getattr(args, "privacy", None),
            "title": getattr(args, "yt_title", "") or "",
            "description": getattr(args, "yt_desc", "") or "",
        },
        "phases": {},
    }
    for ph in PHASES:
        rec = p.state.get("phases", {}).get(ph)
        if rec:
            delivery["phases"][ph] = {
                "done": rec.get("done"),
                "ts": rec.get("ts"),
            }

    data["delivered"].append(delivery)
    save_deliveries(data)
    print(f"== ENTREGA: registrado em {DELIVERIES_FILE}", flush=True)
    return delivery


def find_duplicate_by_slug(slug):
    """Verifica se o slug ja foi entregue (consulta o JSON, nao varre pastas)."""
    data = load_deliveries()
    return any(d.get("slug") == slug for d in data.get("delivered", []))


def find_duplicate_by_prompt(prompt):
    """Verifica se o prompt ja foi entregue (consulta o JSON)."""
    prompt_norm = (prompt or "").strip().lower()
    data = load_deliveries()
    return any(
        (d.get("prompt") or "").strip().lower() == prompt_norm
        for d in data.get("delivered", [])
    )


def cmd_full(args):
    # === DETECAO DE DUPLICIDADE ===
    # Varre projetos existentes antes de iniciar: se o topico ja foi usado,
    # avanca automaticamente para o proximo topico da fila de topics.txt.
    current_prompt = getattr(args, "prompt", None) or ""
    if current_prompt:
        if find_duplicate_project(current_prompt):
            nxt = next_topic_in_queue(current_prompt)
            if nxt:
                print(f"== DUPLICADO: '{current_prompt}' ja foi entregue.", flush=True)
                print(f"== Pulando para o próximo tópico da fila: '{nxt}'", flush=True)
                args.prompt = nxt
                args.slug = slugify(nxt)
            else:
                print(f"== DUPLICADO: '{current_prompt}' ja foi entregue.", flush=True)
                print("== Não há próximo tópico na fila de topics.txt. Nada a fazer.", flush=True)
                return
    p = get_project(args)
    p.ensure_dirs()
    print(f"== ASSUNTO/TEMA: {p.prompt}")
    p.tree()

    # sobrescreve target_duration_s no config.json se --duration passado
    if getattr(args, "duration", None):
        cfg_path = HERE / "config.json"
        cfg = load_json(cfg_path)
        cfg["target_duration_s"] = args.duration
        save_json(cfg_path, cfg)
        print(f"== target_duration_s atualizado para {args.duration}s")

    phases_to_run = PHASES[:]
    if getattr(args, "from_phase", None):
        if args.from_phase == "auto":
            first_missing = next((ph for ph in PHASES if not p.checkpoint(ph)), None)
            phases_to_run = PHASES[PHASES.index(first_missing or "script"):] if first_missing else []
        else:
            phases_to_run = PHASES[PHASES.index(args.from_phase):]
    if getattr(args, "only", None):
        phases_to_run = [ph for ph in PHASES if ph in set(x.strip() for x in args.only.split(","))]
    if getattr(args, "skip", None):
        skipped = set(x.strip() for x in args.skip.split(","))
        phases_to_run = [ph for ph in phases_to_run if ph not in skipped]

    if not phases_to_run:
        print("== Nada a fazer: todos os checkpoints estao completos.")
        return

    print(f"== Planejado: {phases_to_run}")
    t0 = time.time()
    force = getattr(args, "force", False)
    if force:
        for ph in phases_to_run:
            p.reset_phase(ph)

    # quando --publish, adiciona a fase youtube ao plano
    if getattr(args, "publish", False):
        if "youtube" not in phases_to_run:
            phases_to_run.append("youtube")
        print(f"== Planejado (com youtube): {phases_to_run}")

    execute_phases(args, p, phases_to_run, force=force)
    elapsed = time.time() - t0
    print(f"\n== PIPELINE CONCLUIDO em {elapsed:.1f}s")
    print(f"== VIDEO FINAL: {p.video}")
    publish_result = getattr(args, "publish_ok", None) if getattr(args, "publish", False) else None
    write_control_json(p, args, t0, elapsed, publish_result=publish_result)
    record_delivery(p, args, t0, elapsed, publish_result=publish_result)

    # Sincronizacao automática dos bancos globais (imagens + musicas)
    try:
        from sync_bancos import main as sync_bancos_main
        print("== BANCOS: sincronizando imagens e músicas para os bancos globais...", flush=True)
        sync_bancos_main()
    except Exception as e:
        print(f"== BANCOS: falha na sincronização ({e})", flush=True)
    if not getattr(args, "publish", False):
        print("== YOUTUBE: NAO PUBLICADO (use --publish para publicar automaticamente).")
        print(f"== Para publicar depois: python scripts/youtube_upload.py --video \"{p.video}\"")

    # Atualizar metadados de video existente (se --yt-video-id informado)
    if getattr(args, "yt_video_id", ""):
        update_youtube_metadata(p, args)


def cmd_status(args):
    p = get_project(args)
    if not p.state_file.exists():
        print(f"Projeto {p.slug}: sem estado (nunca rodou).")
        p.tree()
        return
    print(f"== Projeto: {p.slug}")
    print(f"== Diretorio: {p.dir}")
    for ph in PHASES:
        rec = p.state.get("phases", {}).get(ph)
        if rec and rec.get("done"):
            err = p.validate_file_phase(ph)
            tag = "OK (checkpoint)" if err is None else f"INVALIDO ({err})"
            print(f"  {ph:11s} {rec['ts']}  {tag}")
        else:
            print(f"  {ph:11s} pendente")
    if p.video.exists():
        print(f"  video: {p.video} ({p.video.stat().st_size} bytes)")


def cmd_reset(args):
    p = get_project(args)
    if getattr(args, "all", False):
        for ph in PHASES:
            p.reset_phase(ph)
        print(f"== checkpoints resetados (arquivos mantidos) para {p.slug}")
        return
    for ph in [x.strip() for x in (args.phase or "").split(",") if x.strip()]:
        if ph not in PHASES:
            raise SystemExit(f"fase desconhecida: {ph} ({','.join(PHASES)})")
        p.reset_phase(ph)
    print("== reset concluido:", args.phase)


def main():
    # Força UTF-8 no stdout/stderr para evitar erro de codificação no Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description="Pipeline de video com checkpoints (full/status/reset)",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    def common(sp, need_prompt=True):
        if need_prompt:
            sp.add_argument("--prompt", help="assunto do video (define o nome do projeto)")
        sp.add_argument("--slug", help="forca o nome do projeto (senao vem do prompt)")
        sp.add_argument("--wait", type=int, default=420)
        sp.add_argument("--pause", type=int, default=8)
        sp.add_argument("--voice", default="pt-BR-ThalitaNeural",
                        help="voz Edge (pt-BR-*) ou voz Gemini (Leda, Achernar, ...)")
        sp.add_argument("--narration-provider", default=None, choices=["edge", "gemini"],
                        help="motor de narracao (padrao: config tts.provider)")
        sp.add_argument("--rate", default="+12%")
        sp.add_argument("--pitch", default="+8Hz")
        sp.add_argument("--style", default="excited")
        sp.add_argument("--workers", type=int, default=4)
        sp.add_argument("--provider", default=None, choices=["gemini", "procedural"])
        sp.add_argument("--gain", type=float, default=None)
        sp.add_argument("--duration", type=int, default=None,
                        help="duracao alvo do video (s) - sobrescreve config.json")
        sp.add_argument("--skip-check", action="store_true",
                        help="pula o npm run check no render (re-render rapido)")
        sp.add_argument("--publish", action="store_true",
                        help="publica no YouTube apos o render")
        sp.add_argument("--privacy", default="public",
                        choices=["private", "unlisted", "public"])
        sp.add_argument("--yt-title", default="")
        sp.add_argument("--yt-tags", default="cachorro,animação,frida,luna")
        sp.add_argument("--yt-desc", default="",
                        help="descricao completa do video (sobrescreve a gerada automaticamente)")
        sp.add_argument("--yt-thumb", default="",
                        help="caminho da imagem de thumbnail (JPG/PNG)")
        sp.add_argument("--default-language", default="pt-BR",
                        help="idioma padrao do video no YouTube (ex: pt-BR)")
        sp.add_argument("--default-audio-language", default="pt-BR",
                        help="idioma do audio/narracao no YouTube (ex: pt-BR)")
        sp.add_argument("--yt-secret", default="",
                        help="caminho do client_secret.json do canal")
        sp.add_argument("--yt-video-id", default="",
                        help="ID de video existente para atualizar apenas metadados (sem upload)")
        sp.add_argument("--yt-kids", action="store_true", default=True,
                        help="marca o video como feito para criancas (COPPA)")
        sp.add_argument("--nao-kids", action="store_true",
                        help="desativa o modo feito para criancas")
        sp.add_argument("--sem-texto", action="store_true", default=True,
                        help="nao gera texto sobreposta nas cenas (apenas imagem + narracao)")

    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("full", help="pipeline completo com checkpoints")
    common(f)
    f.add_argument("--from", dest="from_phase", default="auto",
                   choices=["auto"] + PHASES,
                   help="comeca em uma fase (auto = primeira pendente)")
    f.add_argument("--only", help="roda apenas estas fases, ex: mix,compose")
    f.add_argument("--skip", help="pula estas fases")
    f.add_argument("--force", action="store_true", help="ignora checkpoints e refaz")
    f.add_argument("--no-parallel", action="store_true", help="desativa paralelismo")
    f.set_defaults(func=cmd_full)

    r = sub.add_parser("resume", help="retoma projeto existente pelo slug")
    common(r, need_prompt=False)
    r.add_argument("--from", dest="from_phase", default="auto",
                   choices=["auto"] + PHASES,
                   help="comeca em uma fase (auto = primeira pendente)")
    r.add_argument("--only", help="roda apenas estas fases, ex: mix,compose")
    r.add_argument("--skip", help="pula estas fases")
    r.add_argument("--force", action="store_true", help="ignora checkpoints e refaz")
    r.add_argument("--no-parallel", action="store_true", help="desativa paralelismo")
    r.set_defaults(func=cmd_full)

    s = sub.add_parser("status", help="mostra checkpoints do projeto")
    common(s)
    s.set_defaults(func=cmd_status)

    z = sub.add_parser("reset", help="limpa checkpoints de fases")
    common(z)
    z.add_argument("--phase", default="",
                   help="fases separadas por virgula")
    z.add_argument("--all", action="store_true")
    z.set_defaults(func=cmd_reset)

    args = ap.parse_args()
    if not getattr(args, "prompt", None) and not getattr(args, "slug", None):
        if args.cmd == "full":
            raise SystemExit("ERRO: --full pede --prompt; para retomar use 'resume --slug ...'")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
