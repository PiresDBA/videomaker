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
  projects/<slug>/project-control.json            controle final (observabilidade)
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


===============================================================================
COMANDOS (resumo)
===============================================================================

  full     roda o pipeline completo, criando o projeto a partir do prompt
  resume   retoma um projeto ja existente, localizado pelo --slug
  status   mostra os checkpoints (o que ja foi feito e o que falta)
  reset    limpa checkpoints para refazer fases
  contract mostra o CONTRATO de trabalho e o indice do manual (leia antes
           de mexer em qualquer coisa)


===============================================================================
EXEMPLOS DE USO
===============================================================================

  # 0) PRIMEIRO COMANDO DE QUALQUER SESSAO: leia o contrato e o indice
  python scripts/pipeline.py contract

  # 1) Pipeline completo automatico (retoma de onde parou)
  python scripts/pipeline.py full --prompt "Vídeo engraçado sobre buldogue inglês"

  # 2) Comecar de uma fase especifica (todas as anteriores sao puladas)
  python scripts/pipeline.py full --prompt "Por que o cachorro lambe o seu rosto?" --from narration

  # 3) Rodar somente determinadas fases
  python scripts/pipeline.py full --prompt "Cachorro engraçado" --only mix,compose

  # 4) Pular fases (mantem os demais checkpoints)
  python scripts/pipeline.py full --prompt "Cachorro engraçado" --skip music

  # 5) Ignorar checkpoints e refazer tudo
  python scripts/pipeline.py full --prompt "Cachorro engraçado" --from script --force

  # 6) Retomar projeto existente pelo slug (sem passar prompt de novo)
  python scripts/pipeline.py resume --slug buldogue-ingles-divertido

  # 7) Ver o status dos checkpoints
  python scripts/pipeline.py status --prompt "Cachorro engraçado"

  # 8) Resetar o checkpoint de uma fase (refaz na proxima rodada)
  python scripts/pipeline.py reset --prompt "Cachorro engraçado" --phase images

  # 9) Resetar todos os checkpoints (os arquivos continuam no disco)
  python scripts/pipeline.py reset --prompt "Cachorro engraçado" --all

  # 10) Gerar E publicar no YouTube na mesma rodada
  python scripts/pipeline.py full --prompt "Husky siberiano engraçado" --publish

  # 11) Re-render rapido: refaz mix/compose/render sem o check do HyperFrames
  python scripts/pipeline.py full --prompt "Cachorro engraçado" --from mix --skip-check

  # 12) Narracao com a voz Gemini (alterna Achernar/Leda a cada video)
  python scripts/pipeline.py full --prompt "Cachorro engraçado" --narration-provider gemini

  # 13) Forcar uma voz especifica
  python scripts/pipeline.py full --prompt "Cachorro engraçado" --narration-provider gemini --voice Leda

  # 14) Re-render sem nada mais (so as ultimas fases, em paralelo)
  python scripts/pipeline.py full --prompt "Cachorro engraçado" --from timeline --no-parallel

  # 15) Atualizar so os metadados de um video ja publicado (sem reenviar)
  python scripts/pipeline.py full --slug buldogue-ingles-divertido --yt-video-id kJztp7A7xWI


===============================================================================
ARGUMENTOS COMUNS (valem para full, resume, status e reset)
===============================================================================

--prompt TEXTO
    Assunto do video. Define o nome da pasta do projeto (via slugify) e o
    prompt enviado ao Gemini na fase `script`.
    Exemplo: --prompt "Por que cachorros cheiram o bumbum uns dos outros?"

--slug NOME
    Força o nome da pasta do projeto, ignorando o slug derivado do prompt.
    Comandos que exigem --slug: `resume` (obrigatório), `full` (opcional).
    Exemplo: --slug caes-de-resgate-como-eles-encontram-pess

--wait SEGUNDOS
    Espera máxima por resposta do Gemini Web durante a geração de imagens.
    Padrão: 420. Aumentar quando a conexão estiver lenta.
    Exemplo: --wait 600

--pause SEGUNDOS
    Pausa entre as chamadas ao Gemini Web (evita bloqueio por automacao).
    Padrão: 8. Em conta gratuita do Google, valores menores podem dar 429.
    Exemplo: --pause 15

--voice NOME
    Voz da narração.
      - Edge-TTS (local, sem API): pt-BR-ThalitaNeural, pt-BR-AntonioNeural,
        pt-BR-FranciscaNeural, pt-BR-ThiagoNeural...
      - Gemini TTS (Google AI Studio, precisa de GOOGLE_TTS_API_KEY):
        Leda, Achernar, Kore, Zephyr, Despina...
    Se a voz começar com "pt-BR-" ou terminar em "Neural", o motor Edge e
    usado mesmo com --narration-provider gemini.
    Exemplo: --voice pt-BR-FranciscaNeural

--narration-provider {edge,gemini}
    Motor da narração. "edge" = Edge-TTS local (padrão seguro, sem API).
    "gemini" = Google AI Studio TTS (qualidade superior, consome cota).
    Se omitido, vale config.json -> tts.provider (hoje: "gemini"), com
    fallback automático para Edge-TTS em qualquer falha do Gemini.
    Exemplo: --narration-provider edge

--rate VELOCIDADE
    Velocidade da fala na sintese Edge-TTS (formato Edge: +12%, -10%, +0%).
    Padrão: +12%. Só se aplica ao motor Edge.
    Exemplo: --rate "+0%"

--pitch TOM
    Tom da fala na sintese Edge-TTS (formato Edge: +8Hz, -5Hz, +0Hz).
    Padrão: +8Hz. Só se aplica ao motor Edge.
    Exemplo: --pitch "+0Hz"

--style ESTILO
    Estilo de fala usado pelo gerador Edge-TTS (excited, cheerful, friendly,
    narration, etc.). Affects o emphasis automatico da voz.
    Padrão: excited.
    Exemplo: --style narration

--workers N
    Quantidade de secoes de narracao processadas em paralelo.
    Padrão: 4. Mais workers = mais rapido, mas mais carga de CPU/rede.
    Exemplo: --workers 8

--provider {gemini,procedural}
    Origem da trilha musical.
      - gemini: gera a trilha pelo Gemini Web (Chrome, conta gratuita).
      - procedural: gera a trilha localmente (sem API, sempre disponível).
    Se omitido, usa a trilha do banco local quando houver; o procedural e o
    fallback automatico quando o Gemini falha.
    Exemplo: --provider procedural

--gain DB
    Ganho de audio aplicado na mixagem (narracao + trilha). Negativo abaixa
    a trilha. Exemplo: --gain -6.0 (voz em primeiro plano).

--duration SEGUNDOS
    Duracao alvo do video. Sobrescreve config.json -> target_duration_s e
    guia o roteiro para caber no tempo. Exemplo: --duration 90

--skip-check
    Pula o "npm run check" do HyperFrames na fase render (re-render rapido).
    Útil quando só mudou a narração ou a trilha, não o layout.
    Exemplo: --skip-check

--publish
    Publica no YouTube automaticamente depois do render (adiciona a fase
    `youtube` ao plano). Sem esta flag o video é apenas renderizado.
    Exemplo: --publish

--privacy {private,unlisted,public}
    Visibilidade do video no YouTube. Padrão: public.
    Exemplo: --privacy unlisted

--yt-title TITULO
    Título exato do video no YouTube. Se omitido, usa o titulo do roteiro
    (script.json). Exemplo: --yt-title "Husky siberiano: o cachorro que faz drama"

--yt-tags LISTA
    Tags do video, separadas por virgula. Se omitido, usa a lista padrão do
    canal (15 tags). Exemplo: --yt-tags "husky,siberiano,cachorro,pet,infantil"

--yt-desc DESCRICAO
    Descrição completa do YouTube. Se omitido, é gerada no padrão oficial do
    canal (scripts/description_template.py) a partir do roteiro do projeto.
    Exemplo: --yt-desc "Descrição customizada que substitui a automática."

--yt-thumb CAMINHO
    Imagem de thumbnail (JPG/PNG). Se omitido, usa a primeira imagem de cena
    gerada no projeto. Exemplo: --yt-thumb "C:/videomaker/projects/meu-projeto/capa.jpg"

--default-language IDIOMA
    Idioma padrão do vídeo no YouTube (metadados). Padrão: pt-BR.
    Exemplo: --default-language pt-BR

--default-audio-language IDIOMA
    Idioma do áudio/narração no YouTube (metadados). Padrão: pt-BR.
    Exemplo: --default-audio-language pt-BR

--yt-secret CAMINHO
    Caminho do client_secret.json do canal do YouTube.
    Padrão: scripts/client_secret.json.
    Exemplo: --yt-secret "C:/videomaker/scripts/client_secret-xanpires.json"

--yt-video-id ID
    ID de um vídeo já publicado, para atualizar apenas os metadados
    (título, descrição, tags, thumbnail) sem reenviar o arquivo.
    Exemplo: --yt-video-id kJztp7A7xWI

--yt-kids
    Marca o vídeo como "feito para crianças" (COPPA). É o padrão.
    Exemplo: --yt-kids

--nao-kids
    Desliga a marcação "feito para crianças" (sobrescreve --yt-kids).
    Exemplo: --nao-kids

--sem-texto
    Não gera texto sobreposto nas cenas (apenas imagem + narração). É o
    padrão do canal. Exemplo: --sem-texto


===============================================================================
ARGUMENTOS EXCLUSIVOS DE `full` e `resume`
===============================================================================

--from FASE
    Começa em uma fase específica (auto = primeira pendente).
    Fases: script, scenes, music, images, narration, timeline, mix, compose,
    preprocess, render.
    Exemplo: --from narration

--only LISTA
    Roda apenas estas fases, separadas por vírgula.
    Exemplo: --only mix,compose,render

--skip LISTA
    Pula estas fases, separadas por vírgula (o resto continua).
    Exemplo: --skip music,images

--force
    Ignora os checkpoints e refaz as fases do plano (os arquivos são
    sobrescritos). Exemplo: --force

--no-parallel
    Desativa o paralelismo (fases uma por vez, em ordem). Útil para depurar
    ou quando o Gemini Web bloqueia com várias abas abertas.
    Exemplo: --no-parallel


===============================================================================
ARGUMENTOS EXCLUSIVOS DE `reset`
===============================================================================

--phase LISTA
    Fases cujo checkpoint será limpo, separadas por vírgula.
    Exemplo: --phase images,music

--all
    Limpa o checkpoint de todas as fases (os arquivos físicos são mantidos).
    Exemplo: --all


===============================================================================
AS FASES (ordem de execucao)
===============================================================================

  script       roteiro (s0 abertura, s_intro gancho, s1..sN, s_outro) via
               Gemini Web. Produz artifacts/script.json.
  scenes       divide o roteiro em cenas + prompts de imagem + overlays HTML.
               Produz artifacts/scenes.json, image_prompts.json, scenes/*.html.
  music        trilha instrumental (banco local, Gemini Web ou procedural).
               Produz assets/audio/gemini/bgm_gemini.wav.
  images       uma imagem por cena: banco local (BM25) primeiro, Gemini Web
               depois, com loop de quarentena de 4 tentativas.
  narration    narracao por secao (Edge-TTS local ou Gemini TTS), gera
               assets/audio/narration/*.wav e artifacts/narration_timing.json.
  timeline     linha do tempo com inicio/fim de cada secao.
  mix          mix de narracao + trilha -> assets/audio/final_mix.m4a.
  compose      composicao HyperFrames -> composition.html.
  preprocess   copia/prepara as imagens para o HyperFrames.
  render       renderiza o MP4 final -> output/<slug>.mp4.
  youtube      publica no YouTube (so com --publish). Fora da lista PHASES
               porque e opcional e roda por ultimo.

Grafo de dependencias (DEPS): refazer uma fase caduca as descendentes.
  script    -> scenes, narration, timeline
  scenes    -> preprocess, compose
  images    -> preprocess
  music     -> mix
  narration -> timeline
  timeline  -> mix, compose
  mix       -> render
  compose   -> render
  preprocess-> render
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

# Tags padrao do canal (canal "Frida e Luna"). Usadas quando --yt-tags nao e
# informado. Mesma lista ampliada do youtube_upload.py.
YT_TAGS_PADRAO = (
    "cachorro,animacao,infantil,frida,luna,cachorrinho,desenhoanimado,"
    "videoengraçado,conteúdocriativo,petspride,familia,criancas,"
    "cachorroengraçado,diversão,aprendizado"
)

# Indice do MANUAL_GRAFOS.md, mostrado pelo comando `contract`.
# Serve para o proximo nao gastar token vasculhando o manual inteiro.
INDICE_MANUAL = [
    "§0    CONTRATO - a regra de ouro (leia primeiro)",
    "§1    Resumo do problema e das correcoes",
    "§1.7  Voz recomendada / §1.8 Musica procedural",
    "§3    Grafo do pipeline (Mermaid)",
    "§4    Grafo de dependencias (invalidacao em cascata)",
    "§10   Solucao de problemas",
    "§11   Executor diario (daily_runner.py)",
    "§20   Calendario de agendamento de videos",
    "§23   Atualizar metadados de video ja enviado",
    "§34   Narração em portugues com caracteres especiais",
    "§36   Padrao oficial de descricao do canal",
    "§37   Documentacao do pipeline (comandos e argumentos)",
    "§38   Convenção: branch -> grafo -> push",
    "§39   Contrato de trabalho (detalhe)",
]

SCRIPTS = {
    "script_from_prompt": HERE / "generate_script_from_prompt.py",
    "scenes_from_script": HERE / "generate_scenes_and_prompts.py",
    "scene_htmls": HERE / "generate_scene_htmls.py",
    "fetch_images": HERE / "fetch_images.py",
    "flow_fetch": HERE / "flow_fetch.py",
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
    """Le um JSON do disco (UTF-8). Levanta excecao se o arquivo estiver corrompido."""
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, data):
    """Grava um JSON no disco (UTF-8, indent=2, sem escapar acentos),
    criando o diretorio pai se preciso."""
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
    """Normaliza um texto para comparacao: sem acento, minusculo, sem
    espacos duplicados. Usado na busca do banco de imagens."""
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
    """Executa um comando externo (subprocess) e levanta RuntimeError se falhar.

    cmd    lista de argumentos (ex: [sys.executable, "script.py", "--x", "1"])
    label  texto mostrado no log e usado na mensagem de erro
    """
    print(f"== {label or ' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        msg = label or " ".join(cmd)
        raise RuntimeError(f"{msg} (exit {r.returncode})")
    return r


# ---------------------------------------------------------------- estado ---

class Project:
    """Estado do projeto: caminhos + checkpoints (project.json).

    Cada instancia sabe onde ficam os artefatos do projeto (roteiro, cenas,
    imagens, audio, composicao, video) e carrega o project.json, que guarda
    quais fases ja foram concluidas.

    Exemplo:
        p = Project("cachorro-engracado", "Vídeo engraçado sobre cachorro")
        p.ensure_dirs()
        print(p.checkpoint("script"))   # True se a fase script ja esta ok
    """

    def __init__(self, slug, prompt=None):
        """Cria o objeto Project e carrega o project.json (se existir).

        slug    nome da pasta do projeto (ex: "cachorro-engracado")
        prompt  assunto original do video (usado como fallback)
        """
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
        """Carrega o project.json (checkpoints + historico). Cria um vazio se
        o arquivo ainda nao existir ou estiver corrompido."""
        if self.state_file.exists():
            try:
                return load_json(self.state_file)
            except Exception:
                pass
        st = {"slug": self.slug, "prompt": self.prompt, "phases": {}, "history": []}
        return st

    def save_state(self):
        """Grava o project.json com os checkpoints e o historico atualizados."""
        st = self.state
        st.setdefault("phases", {})
        st.setdefault("history", [])
        if self.prompt:
            st["prompt"] = self.prompt
        save_json(self.state_file, st)

    def mark(self, phase, ok=True, detail=""):
        """Marca uma fase como concluida (ou nao) e registra no historico.

        phase   nome da fase (script, scenes, images, ...)
        ok      True = concluida, False = pendente
        detail  texto livre com o caminho do artefato gerado
        """
        st = self.state
        st["phases"][phase] = {"done": bool(ok), "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                               "detail": detail}
        if ok:
            st["history"].append({"ts": st["phases"][phase]["ts"], "phase": phase,
                                  "event": "done", "detail": detail[:200]})
        self.save_state()

    def reset_phase(self, phase):
        """Apaga o checkpoint de uma fase (os arquivos fisicos sao mantidos).
        A fase volta a ser executada na proxima rodada."""
        self.state.setdefault("phases", {}).pop(phase, None)
        self.save_state()

    def is_done(self, phase, force=False):
        """True se a fase esta marcada como concluida (force ignora o estado)."""
        if force:
            return False
        rec = self.state.get("phases", {}).get(phase)
        return bool(rec and rec.get("done"))

    def validate_file_phase(self, phase):
        """Validacao fisica extra: arquivos existem / JSON valido / contagem.

        Retorna None quando a fase esta integra, ou a mensagem do problema
        (ex: "faltam imagens: [...]", "arquivo ausente").
        """
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
        """True = pode pular (checkpoint valido). False = precisa rodar.

        Alem do flag do project.json, roda a validacao fisica dos arquivos:
        se o checkpoint diz "feito" mas o artefato sumiu, a fase e refeita."""
        if self.is_done(phase, force=force):
            err = self.validate_file_phase(phase)
            if err is None:
                print(f"== CHECKPOINT {phase}: feito em {self.state['phases'][phase]['ts']} -> pulando")
                return True
            print(f"== CHECKPOINT {phase}: invalido ({err}) -> vai refazer")
        return False

    def ensure_dirs(self):
        """Cria (se preciso) todos os diretorios do projeto."""
        for d in (self.dir, self.artifacts, self.scenes_dir, self.images_src,
                  self.narration_dir, self.audio_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)

    def tree(self):
        """Imprime no console a arvore de arquivos do projeto."""
        print(f"\n== Projeto: {self.dir}")
        for p in (self.script, self.scenes_json, self.image_prompts,
                  self.narration_timing, self.timeline_json, self.bgm,
                  self.narration_full, self.final_mix, self.composition,
                  self.output_dir, self.video, self.state_file):
            print(f"    {p}")
        print()


# ---------------------------------------------------------------- fases ----

def phase_script(args, p: Project):
    """FASE 1/10 - Roteiro.

    Chama generate_script_from_prompt.py (Gemini Web via Chrome, conta
    gratuita) e grava artifacts/script.json com o titulo e as secoes
    (s0 abertura, s_intro gancho, s1..sN conteudo, s_outro encerramento).
    O contrato de narracao e validado aqui (validate_contract).

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only script
    """
    run([sys.executable, str(SCRIPTS["script_from_prompt"]),
         "--prompt", args.prompt or p.prompt or p.slug,
         "--out", str(p.script)],
        "FASE script: roteiro via Gemini WEB (Chrome, conta gratuita)")
    p.mark("script", detail=str(p.script))


def phase_scenes(args, p: Project):
    """FASE 2/10 - Cenas e overlays (100% local, deterministico).

    1) generate_scenes_and_prompts.py: divide o roteiro em cenas, grava
       artifacts/scenes.json e artifacts/image_prompts.json.
    2) generate_scene_htmls.py: gera os overlays de texto scenes/sN.html.

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only scenes
    """
    cmd = [sys.executable, str(SCRIPTS["scenes_from_script"]),
           "--script", str(p.script),
           "--scenes-out", str(p.scenes_json),
           "--prompts-out", str(p.image_prompts)]
    if getattr(args, "scene_mode", None):
        cmd += ["--scene-mode", args.scene_mode]
    for opt, val in (("--max-images-per-section", getattr(args, "max_images_per_section", None)),
                     ("--min-words-per-beat", getattr(args, "min_words_per_beat", None)),
                     ("--max-words-per-beat", getattr(args, "max_words_per_beat", None))):
        if val is not None:
            cmd += [opt, str(val)]
    run(cmd, "FASE scenes: cenas + prompts (local deterministico)")
    run([sys.executable, str(SCRIPTS["scene_htmls"]),
         "--script", str(p.script),
         "--scenes", str(p.scenes_json),
         "--out-dir", str(p.scenes_dir)],
        "FASE scenes: overlays HTML (local deterministico)")
    p.mark("scenes", detail=f"{p.scenes_json}")


def phase_images(args, p: Project):
    """FASE 3/10 - Imagens das cenas.

    Gera imagens uma por uma com loop de quarentena (ate 4 tentativas).
    Antes de gerar via Gemini, verifica se existe imagem adequada no banco
    local (banco de imagens / indice_midia.db, busca BM25). Se achar, copia para o
    projeto e pula a geracao.

    Argumentos usados:
        --wait / --pause  repassados ao fetch_images.py (Gemini Web)

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only images
    """
    prompts = load_json(p.image_prompts)
    # ids de imagem = chaves do image_prompts.json (sem o _help)
    image_ids = [k for k in prompts.keys() if not k.startswith("_")]
    out_dir = p.dir / "assets" / "images" / "gemini" / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    fonte = ("Google Flow (sem banco local)" if getattr(args, "sem_banco", False)
             else "banco local primeiro, Flow/Gemini se nao achar")
    print(f"== FASE images: {len(image_ids)} imagem(ns) ({fonte})", flush=True)

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
        caminho_banco = None
        if not getattr(args, "sem_banco", False):
            caminho_banco = buscar_imagem_banco(desc_busca, limite=5)
        if caminho_banco:
            try:
                copiar_para_projeto(Path(caminho_banco), out_dir, nome + ".jpg")
                print(f"  [{nome}] OK (banco local: {Path(caminho_banco).name})", flush=True)
                return True
            except Exception as e:
                print(f"  [{nome}] falhou ao copiar do banco ({e})", flush=True)
        if getattr(args, "apenas_banco", False):
            # apenas banco: nao gera via Flow nem Gemini se nao achar no banco local
            print(f"  [{nome}] nao encontrado no banco local (apenas-banco, pulando geracao)", flush=True)
            return False

        # 2) Nao achou no banco: gera via Flow (principal) ou Gemini (fallback)
        prompt_texto = prompts.get(nome, "")
        rc, name, size = run_single_fetch(nome, prompt_texto, out_dir, args)
        ok = rc == 0 and size > 0
        status = "OK" if ok else f"FALHA (rc={rc} bytes={size})"
        print(f"  [{name}] {status}", flush=True)
        return ok

    def run_single_fetch(nome: str, prompt_texto: str, out_dir: Path, args) -> tuple:
        """Chama flow_fetch.py (principal) ou fetch_images.py (fallback Gemini) para uma imagem."""
        # 1) Tentar Google Flow primeiro
        cmd_flow = [sys.executable, str(SCRIPTS["flow_fetch"]),
                    "--kind", "image",
                    "--prompt", prompt_texto,
                    "--name", nome,
                    "--project-dir", str(p.dir),
                    "--out-dir", str(out_dir),
                    "--wait", str(args.wait),
                    "--pause", str(args.pause),
                    "--skip-confirm"]
        r = subprocess.run(cmd_flow)
        jpg = out_dir / (nome + ".jpg")
        size = jpg.stat().st_size if jpg.exists() else 0
        if r.returncode == 0 and size > 0:
            return r.returncode, nome, size

        # 2) Fallback: Gemini Web
        print(f"  [{nome}] flow_fetch falhou (rc={r.returncode}), tentando Gemini como fallback", flush=True)
        cmd_gemini = [sys.executable, str(SCRIPTS["fetch_images"]),
                      "--proj", str(p.dir),
                      "--single", nome,
                      "--wait", str(args.wait),
                      "--pause", str(args.pause)]
        r2 = subprocess.run(cmd_gemini)
        size = jpg.stat().st_size if jpg.exists() else 0
        return r2.returncode, nome, size

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
    """FASE 4/10 - Trilha sonora instrumental.

    Ordem de preferencia:
      1) Banco local ("banco de musicas"), com rotacao sem repetir trilha
         entre projetos (LRU quando o acervo esgota);
      2) Gemini Web (fetch_music_gemini.py), 2 tentativas;
      3) Trilha procedural local (gen_music_procedural.py) - sempre disponivel.

    Argumentos usados:
        --provider {gemini,procedural}  forca a origem da trilha
        --wait                          espera pelo Gemini Web

    Saida: assets/audio/gemini/bgm_gemini.wav (ou assets/audio/music/bgm_procedural.wav)

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only music --provider procedural
    """
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
    """FASE 5/10 - Narracao por secao.

    Motor escolhido por --narration-provider (ou config.json -> tts.provider):
      - "edge":  gen_narration_edge.py, local e sem API (padrao seguro).
      - "gemini": gen_narration_gemini_sections.py, Google AI Studio
                  (GOOGLE_TTS_API_KEY). A voz alterna entre
                  config.json -> tts.gemini_voices (Achernar/Leda) a cada
                  video, a menos que --voice force uma voz especifica.
      - Se o Gemini falhar (429/401/...) e config.json -> tts.edge_fallback
        estiver ligado, cai automaticamente para o Edge-TTS e registra
        "fallback_from": "gemini" no project.json.

    Argumentos usados:
        --voice / --narration-provider / --rate / --pitch / --style / --workers

    Saida: assets/audio/narration/*.wav + artifacts/narration_timing.json

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only narration \
            --narration-provider gemini --voice Leda
    """
    cfg = load_json(HERE / "config.json")
    tts = cfg.get("tts", {})
    provider = (getattr(args, "narration_provider", None) or tts.get("provider") or "edge").lower()
    if provider not in ("edge", "gemini"):
        provider = "edge"

    voice_arg = (getattr(args, "voice", "") or "").strip()
    edge_style = (not voice_arg) or voice_arg.lower().startswith("pt-br-") \
        or voice_arg.lower().endswith("neural")

    def _run_edge(voice, rate, pitch, style, workers, label):
        """Gera a narracao com Edge-TTS (local, sem API) e registra no estado."""
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
    """FASE 6/10 - Linha do tempo (local).

    build_timeline.py calcula o inicio/fim de cada secao a partir da duracao
    real da narracao e grava artifacts/timeline.json.
    IMPORTANTE: a timeline e reescrita aqui, entao refazer a narracao
    invalida timeline, mix e compose (ver DEPS).

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only timeline
    """
    run([sys.executable, str(SCRIPTS["build_timeline"]),
         "--proj", str(p.dir)],
        "FASE timeline: linha do tempo (local)")
    p.mark("timeline", detail=str(p.timeline_json))


def phase_mix(args, p: Project):
    """FASE 7/10 - Mix de audio (narracao + trilha).

    mix_audio.py combina a narracao concatenada com a trilha e normaliza o
    volume, gravando assets/audio/final_mix.m4a.

    Argumentos usados:
        --provider {gemini,procedural}  origem da trilha na mixagem
        --gain DB                        ganho aplicado na mix (padrao do mix_audio.py)

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only mix --gain -6.0
    """
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
    """FASE 8/10 - Composicao HyperFrames (local).

    build_composition.py monta composition.html a partir da timeline, das
    cenas e dos overlays HTML. Se a timeline mudou, a composicao PRECISA
    ser refeita antes do render (ver MANUAL_GRAFOS.md secao 1.5).

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only compose
    """
    run([sys.executable, str(SCRIPTS["build_composition"]),
         "--timeline", str(p.timeline_json),
         "--scenes", str(p.scenes_json),
         "--scenes-dir", str(p.scenes_dir),
         "--proj", str(p.dir),
         "--out", str(p.composition)],
        "FASE compose: composicao HyperFrames (local)")
    p.mark("compose", detail=str(p.composition))


def phase_preprocess(args, p: Project):
    """FASE 9/10 - Preprocessamento das imagens (local).

    preprocess_images.py copia/ajusta as imagens do projeto para a pasta de
    assets do HyperFrames (HF_DIR/assets/images), no tamanho e formato que o
    renderizador espera.

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only preprocess
    """
    run([sys.executable, str(SCRIPTS["preprocess_images"]),
         "--proj", str(p.dir),
         "--scenes", str(p.scenes_json),
         "--hf-dir", str(HF_DIR)],
        "FASE preprocess: imagens para o HyperFrames (local)")
    p.mark("preprocess", detail="copiado para " + str(HF_DIR / "assets" / "images"))


def phase_render(args, p: Project):
    """FASE 10/10 - Render do video final.

    Chama render.ps1 (HyperFrames) com a composicao e o mix, gerando
    output/<slug>.mp4. Depois roda verify_output.py para checar o arquivo.

    Argumentos usados:
        --skip-check  pula o "npm run check" do HyperFrames (re-render rapido)

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --only render --skip-check
    """
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
    """FASE EXTRA (youtube) - Publica o MP4 no YouTube.

    So roda quando o comando usa --publish. Chama youtube_upload.py com o
    titulo, a descricao no padrao oficial do canal, as tags, a thumbnail e a
    privacidade pedidas.

    Descricao: usa --yt-desc se informado; senao gera no padrao do canal
    (scripts/description_template.py) a partir do roteiro do projeto.
    Thumbnail: usa --yt-thumb se informado; senao a primeira imagem de cena.

    Argumentos usados:
        --publish --privacy --yt-title --yt-desc --yt-tags --yt-thumb
        --yt-secret --yt-kids --nao-kids --default-language
        --default-audio-language

    Exemplo:
        python scripts/pipeline.py full --prompt "Husky engraçado" --publish \
            --privacy unlisted --yt-title "Husky que faz drama"
    """
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

    # Descricao no PADRAO OFICIAL DO CANAL (scripts/description_template.py).
    # IMPORTANTE: sem isto o pipeline passaria uma descricao curta e o
    # youtube_upload.py nunca usaria o roteiro do projeto (que e o que gera a
    # descricao rica). Nunca montar a descricao na mao aqui.
    from description_template import build_description, extract_storyline, read_script

    script = read_script(p.dir) or {}
    auto_desc = build_description(title, extract_storyline(script))
    desc = (getattr(args, "yt_desc", "") or "").strip() or auto_desc
    tags = (getattr(args, "yt_tags", "") or "").strip() or YT_TAGS_PADRAO
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
        """Percorre o grafo DEPS recursivamente, caducando os descendentes."""
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
    """Executa as fases do plano, respeitando os checkpoints.

    Paralelismo: a fase `music` pode rodar em paralelo com script/scenes,
    mas SEMPRE antes de `images` (evita conflito de Chrome/Gemini Web).
    As demais fases rodam em sequencia, porque cada uma depende da
    anterior.

    phases_to_run  lista de fases a executar (inclui "youtube" se for extra)
    force          ignora os checkpoints e refaz as fases
    """
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
    """Monta o objeto Project a partir dos argumentos (--slug tem prioridade).

    Se nenhum dos dois for informado, encerra com uma mensagem de erro
    explicando o uso correto.
    """
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
    """Fase publish: envia o MP4 para o YouTube (youtube_upload.py).

    Atalho legado: delega para phase_youtube(), que e a implementacao
    mantida. Existe para compatibilidade com quem chamava esta funcao
    diretamente.

    Exemplo:
        python scripts/pipeline.py full --prompt "Cachorro engraçado" --publish
    """
    return phase_youtube(args, p)


def update_youtube_metadata(p: Project, args):
    """Atualiza metadados (titulo, descricao, tags, thumbnail) de um video ja enviado ao YouTube.

    Nao reenvia o video: so chama youtube_update.py com o --yt-video-id.
    A descricao usa --yt-desc se informado; senao e gerada no padrao oficial
    do canal a partir do roteiro do projeto.

    Exemplo:
        python scripts/pipeline.py full --slug cachorro-engracado \
            --yt-video-id kJztp7A7xWI --yt-title "Novo titulo"
    """
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

    # Descricao: usa --yt-desc se informado; senao gera no padrao do canal
    # a partir do roteiro do projeto (fonte unica da verdade).
    from description_template import build_description, extract_storyline, read_script

    script = read_script(p.dir) or {}
    desc = (getattr(args, "yt_desc", "") or "").strip()
    if not desc:
        desc = build_description(title, extract_storyline(script))

    tags = (getattr(args, "yt_tags", "") or "").strip() or YT_TAGS_PADRAO
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
            """True se o caminho existir no disco (nunca levanta excecao)."""
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
    """Caminho da pasta do ffmpeg configurada em config.json -> ffmpeg_dir."""
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
    """Grava a lista global de entregas em projects-deliveries.json."""
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
    """Comando `full` / `resume` - executa o pipeline.

    Fluxo:
      1) detecta duplicidade (tema ja entregue -> avanca para a fila de
         topics.txt);
      2) monta o plano de fases conforme --from / --only / --skip;
      3) executa as fases com checkpoint (pula o que ja esta pronto);
      4) grava project-control.json e registra a entrega;
      5) sincroniza os bancos globais de imagens e musicas;
      6) publica no YouTube se --publish (ou atualiza metadados se
         --yt-video-id).

    Exemplos:
        python scripts/pipeline.py full --prompt "Cachorro engraçado"
        python scripts/pipeline.py full --prompt "Cachorro engraçado" --from narration
        python scripts/pipeline.py resume --slug cachorro-engracado --only mix,compose
    """
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
    """Comando `status` - mostra os checkpoints do projeto.

    Para cada fase mostra a data e se o checkpoint ainda e valido (a
    validacao fisica dos arquivos pode invalidar um checkpoint marcado como
    feito). No fim mostra o caminho e o tamanho do video final.

    Exemplo:
        python scripts/pipeline.py status --prompt "Cachorro engraçado"
        python scripts/pipeline.py status --slug cachorro-engracado
    """
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
    """Comando `reset` - limpa checkpoints para refazer fases.

    Só o checkpoint e apagado: os arquivos continuam no disco e sao
    reaproveitados na proxima execucao (quando a fase roda de novo).

    Exemplos:
        python scripts/pipeline.py reset --prompt "Cachorro engraçado" --phase images
        python scripts/pipeline.py reset --prompt "Cachorro engraçado" --phase images,music
        python scripts/pipeline.py reset --prompt "Cachorro engraçado" --all
    """
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


def cmd_contract(args):
    """Comando `contract` - mostra o contrato de trabalho e o indice do manual.

    E o ponto de partida de qualquer sessao: imprime as regras que evitam
    refazer o que ja esta pronto, desfazer o que ja estava ok e gastar token
    com o que ja esta documentado.

    Exemplo:
        python scripts/pipeline.py contract
    """
    print("=" * 74)
    print("CONTRATO DE TRABALHO - Videomaker")
    print("=" * 74)
    print("")
    print("REGRA DE OURO")
    print("  Antes de escrever qualquer codigo, leia:")
    print("    1) MANUAL_GRAFOS.md  - o que ja foi feito, como esta e por que")
    print("    2) CONTRATO.md       - as regras do jogo")
    print("    3) este arquivo      - docstring do topo: comandos e argumentos")
    print("")
    print("  O que esta documentado no manual JA ESTA FEITO: nao refaca.")
    print("  O que esta documentado no manual NAO ESTA QUEBRADO: nao desfaca.")
    print("")
    print("AS 4 REGRAS")
    print("  1. Leia antes de mexer (manual + contrato + docstring do pipeline)")
    print("  2. Branch antes de alterar:  git checkout -b feature/nome-curto")
    print("  3. O MANUAL_GRAFOS.md vai no MESMO COMMIT da mudanca")
    print("  4. Push so depois do manual e dos checks")
    print("     Ordem fixa: branch -> codigo -> grafo/manual -> checks -> commit -> push")
    print("")
    print("O QUE ATUALIZAR NO MANUAL QUANDO MEXER EM...")
    print("  fluxo / fase / dependencia .... §3 e §4 (grafo) + §30.7")
    print("  CLI / argumento ................ §37")
    print("  descricao do YouTube ........... §3 (fase youtube) + §36")
    print("  narracao / voz / musica ........ §3 + §1.7 / §1.8")
    print("  regra de processo .............. nova secao no fim do manual")
    print("")
    print("INDICE RAPIDO DO MANUAL")
    for linha in INDICE_MANUAL:
        print("  %s" % linha)
    print("")
    print("CHECKS ANTES DO PUSH")
    print("  python scripts/check_manual.py           # manual em dia com o codigo?")
    print("  python scripts/check_projects.py         # descricoes no padrao?")
    print("  python scripts/smoke_test_description.py # padrao de descricao ok?")
    print("")
    print("O manual e a memoria do produto. Se nao esta la, nao existe.")
    print("=" * 74)
    return 0


def main():
    """Ponto de entrada da CLI: monta o argparse e despacha para o comando.

    Comandos:
        full     pipeline completo (cria/retoma o projeto pelo --prompt)
        resume   retoma um projeto existente pelo --slug
        status   mostra os checkpoints do projeto
        reset    limpa checkpoints de fases

    Exemplos:
        python scripts/pipeline.py full --prompt "Cachorro engraçado"
        python scripts/pipeline.py resume --slug cachorro-engracado
        python scripts/pipeline.py status --slug cachorro-engracado
        python scripts/pipeline.py reset --slug cachorro-engracado --phase images
    """
    # Força UTF-8 no stdout/stderr para evitar erro de codificação no Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description="Pipeline de video com checkpoints (full/status/reset)",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    def common(sp, need_prompt=True):
        """Registra os argumentos compartilhados por full/resume/status/reset.

        As strings de help sao o "manual" visivel em --help; a explicacao
        completa com exemplos esta no docstring do modulo (topo do arquivo).
        """
        if need_prompt:
            sp.add_argument(
                "--prompt",
                help='assunto do video (define a pasta do projeto). Ex: --prompt "Por que o cachorro lambe o seu rosto?"')
        sp.add_argument(
            "--slug",
            help="forca o nome da pasta do projeto (sem derivar do prompt). Ex: --slug caes-de-resgate")
        sp.add_argument(
            "--wait", type=int, default=420,
            help="espera maxima (s) por resposta do Gemini Web nas imagens. Padrao: 420. Ex: --wait 600")
        sp.add_argument(
            "--pause", type=int, default=8,
            help="pausa (s) entre chamadas ao Gemini Web (anti-bloqueio). Padrao: 8. Ex: --pause 15")
        sp.add_argument(
            "--voice", default="pt-BR-ThalitaNeural",
            help="voz da narracao. Edge: pt-BR-ThalitaNeural, pt-BR-FranciscaNeural. "
                 "Gemini: Leda, Achernar, Kore, Zephyr. Ex: --voice Leda")
        sp.add_argument(
            "--narration-provider", default=None, choices=["edge", "gemini"],
            help="motor da narracao. edge = local sem API (padrao seguro); "
                 "gemini = Google AI Studio (fallback automatico para edge). "
                 "Padrao: config.json tts.provider. Ex: --narration-provider edge")
        sp.add_argument(
            "--rate", default="+12%",
            help="velocidade da fala (Edge-TTS). Padrao: +12%%. Ex: --rate +0%%")
        sp.add_argument(
            "--pitch", default="+8Hz",
            help="tom da fala (Edge-TTS). Padrao: +8Hz. Ex: --pitch +0Hz")
        sp.add_argument(
            "--style", default="excited",
            help="estilo de fala do Edge-TTS (excited, cheerful, narration). Padrao: excited")
        sp.add_argument(
            "--workers", type=int, default=4,
            help="secoes de narracao em paralelo. Padrao: 4. Ex: --workers 8")
        sp.add_argument(
            "--provider", default=None, choices=["gemini", "procedural"],
            help="origem da trilha musical. gemini = Gemini Web; procedural = local sem API. "
                 "Ex: --provider procedural")
        sp.add_argument(
            "--gain", type=float, default=None,
            help="ganho (dB) da mix narracao+trilha; negativo abaixa a trilha. Ex: --gain -6.0")
        sp.add_argument(
            "--duration", type=int, default=None,
            help="duracao alvo do video (s) - sobrescreve config.json target_duration_s. Ex: --duration 90")
        sp.add_argument(
            "--skip-check", action="store_true",
            help="pula o 'npm run check' do HyperFrames no render (re-render rapido)")
        sp.add_argument(
            "--publish", action="store_true",
            help="publica no YouTube depois do render (adiciona a fase youtube)")
        sp.add_argument(
            "--privacy", default="public", choices=["private", "unlisted", "public"],
            help="visibilidade no YouTube. Padrao: public. Ex: --privacy unlisted")
        sp.add_argument(
            "--yt-title", default="",
            help="titulo exato no YouTube (padrao: titulo do roteiro). Ex: --yt-title 'Husky que faz drama'")
        sp.add_argument(
            "--yt-tags", default="",
            help="tags do YouTube separadas por virgula (padrao: lista do canal). "
                 "Ex: --yt-tags 'husky,siberiano,cachorro,pet'")
        sp.add_argument(
            "--yt-desc", default="",
            help="descricao completa do video (padrao: gerada no padrao oficial do canal). "
                 "Ex: --yt-desc 'Descricao customizada.'")
        sp.add_argument(
            "--yt-thumb", default="",
            help="imagem de thumbnail JPG/PNG (padrao: primeira imagem de cena). "
                 "Ex: --yt-thumb 'C:\\videomaker\\projects\\meu-projeto\\capa.jpg'")
        sp.add_argument(
            "--default-language", default="pt-BR",
            help="idioma padrao do video no YouTube. Padrao: pt-BR")
        sp.add_argument(
            "--default-audio-language", default="pt-BR",
            help="idioma do audio/narracao no YouTube. Padrao: pt-BR")
        sp.add_argument(
            "--yt-secret", default="",
            help="caminho do client_secret.json do canal (padrao: scripts/client_secret.json). "
                 "Ex: --yt-secret 'C:\\videomaker\\scripts\\client_secret-xanpires.json'")
        sp.add_argument(
            "--yt-video-id", default="",
            help="ID de video existente para atualizar apenas metadados (sem upload). "
                 "Ex: --yt-video-id kJztp7A7xWI")
        sp.add_argument(
            "--yt-kids", action="store_true", default=True,
            help="marca o video como feito para criancas (COPPA) - padrao do canal")
        sp.add_argument(
            "--nao-kids", action="store_true",
            help="desativa o modo feito para criancas (sobrescreve --yt-kids)")
        sp.add_argument(
            "--sem-texto", action="store_true", default=True,
            help="nao gera texto sobreposta nas cenas (apenas imagem + narracao) - padrao")
        sp.add_argument(
            "--apenas-banco", action="store_true",
            help="fase imagens pesquisa SOMENTE no banco de imagens local; "
                 "nao gera via Google Flow nem Gemini se nao encontrar no banco. "
                 "Ex: --apenas-banco")
        sp.add_argument(
            "--sem-banco", action="store_true",
            help="fase imagens IGNORA o banco local e gera todas as imagens novas "
                 "via Google Flow (com fallback Gemini). Ex: --sem-banco")
        sp.add_argument(
            "--scene-mode", default="beats", choices=["beats", "two"],
            help="como dividir as cenas: beats (padrao) = uma imagem por pausa de "
                 "fala (sincronizada ao timestamp); two = duas imagens fixas por "
                 "cena (comportamento legado). Ex: --scene-mode two")
        sp.add_argument(
            "--max-images-per-section", type=int, default=None,
            help="modo beats: teto de imagens por secao (padrao: config scene_density). "
                 "Ex: --max-images-per-section 5")
        sp.add_argument(
            "--min-words-per-beat", type=int, default=None,
            help="modo beats: minimo de palavras por batida (pausa). "
                 "Ex: --min-words-per-beat 6")
        sp.add_argument(
            "--max-words-per-beat", type=int, default=None,
            help="modo beats: maximo de palavras por batida; menor = mais imagens. "
                 "Ex: --max-words-per-beat 12")

    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser(
        "full",
        help="pipeline completo com checkpoints (cria/retoma o projeto pelo --prompt)",
        description="Roda o pipeline completo. Ex: "
                    "python scripts/pipeline.py full --prompt \"Cachorro engraçado\"",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    common(f)
    f.add_argument("--from", dest="from_phase", default="auto",
                   choices=["auto"] + PHASES,
                   help="comeca em uma fase (auto = primeira pendente). Ex: --from narration")
    f.add_argument("--only", help="roda apenas estas fases, ex: --only mix,compose,render")
    f.add_argument("--skip", help="pula estas fases, ex: --skip music,images")
    f.add_argument("--force", action="store_true", help="ignora checkpoints e refaz")
    f.add_argument("--no-parallel", action="store_true", help="desativa paralelismo")
    f.set_defaults(func=cmd_full)

    r = sub.add_parser(
        "resume",
        help="retoma projeto existente pelo slug (sem passar --prompt)",
        description="Retoma um projeto ja existente. Ex: "
                    "python scripts/pipeline.py resume --slug caes-de-resgate-como-eles-encontram-pess",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    common(r, need_prompt=False)
    r.add_argument("--from", dest="from_phase", default="auto",
                   choices=["auto"] + PHASES,
                   help="comeca em uma fase (auto = primeira pendente). Ex: --from narration")
    r.add_argument("--only", help="roda apenas estas fases, ex: --only mix,compose,render")
    r.add_argument("--skip", help="pula estas fases, ex: --skip music,images")
    r.add_argument("--force", action="store_true", help="ignora checkpoints e refaz")
    r.add_argument("--no-parallel", action="store_true", help="desativa paralelismo")
    r.set_defaults(func=cmd_full)

    s = sub.add_parser(
        "status",
        help="mostra os checkpoints do projeto (o que ja foi feito e o que falta)",
        description="Mostra o status das fases. Ex: "
                    "python scripts/pipeline.py status --prompt \"Cachorro engraçado\"",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    common(s)
    s.set_defaults(func=cmd_status)

    z = sub.add_parser(
        "reset",
        help="limpa checkpoints de fases (os arquivos fisicos sao mantidos)",
        description="Limpa checkpoints. Ex: "
                    "python scripts/pipeline.py reset --prompt \"Cachorro engraçado\" --phase images",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    common(z)
    z.add_argument("--phase", default="",
                   help="fases separadas por virgula. Ex: --phase images,music")
    z.add_argument("--all", action="store_true",
                   help="limpa o checkpoint de todas as fases")
    z.set_defaults(func=cmd_reset)

    c = sub.add_parser(
        "contract",
        help="mostra o CONTRATO de trabalho e o indice do manual (leia antes de mexer)",
        description="Leitura obrigatoria antes de qualquer mudanca. Ex: "
                    "python scripts/pipeline.py contract",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    c.set_defaults(func=cmd_contract)

    args = ap.parse_args()
    if not getattr(args, "prompt", None) and not getattr(args, "slug", None):
        if args.cmd == "full":
            raise SystemExit("ERRO: --full pede --prompt; para retomar use 'resume --slug ...'")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
