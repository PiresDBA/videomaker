# -*- coding: utf-8 -*-
"""
Gera UM capitulo em 3 idiomas (PT, EN, ES) a partir de um unico prompt,
REAPROVEITANDO tudo que ja esta pronto (roteiro, cenas, imagens, narracao,
legendas) e gerando por idioma apenas: traducao do roteiro, overlays, narração,
legendas, timeline, mix, compose e render.

Regras do produto (AUDITORIA 2026-11-12):
  * IMAGEM: SO pelo Google Flow (gerador oficial). flow_fetch injeta
    automaticamente a referencia dos personagens Frida e Luna criados no Flow.
    O Gemini NUNCA gera imagem (o fallback antigo gerava cachorros aleatorios
    sem referencia). Se o Flow falhar: quarentena + AVISO para o usuario abrir
    o Flow - nunca gerar no Gemini.
  * Continuidade: ao gerar uma imagem nova, a ultima imagem gerada do projeto
    e colada como --ref-image (base para a proxima).
  * Nada regera artefato pronto: script, scenes, imagens, traducao, narracao,
    legendas e musica sao pulados se ja existirem.
  * Overlays por idioma: scenes/<lang>/ gerados a partir de script_<lang>.json
    (o texto de abertura fica no idioma do video).
  * Images/scenes/roteiro PT sao compartilhados; por idioma muda apenas a
    lingua da narracao/overlays/legendas - o cenario (imagens) e o mesmo,
    garantindo que o video comeca e termina no mesmo lugar.

Fluxo:
  1) script  -> artifacts/script.json (PT original; pulado se existe)
  2) scenes  -> artifacts/scenes.json + image_prompts.json (pulado se existe)
  3) images  -> 1 imagem por cena via Google Flow (pula as que ja existem)
  4) music   -> banco local -> Gemini -> procedural (pula se bgm ja existe)
  5) Para CADA idioma (pt, en, es):
       - traducao do roteiro (script_<lang>.json; pulada se existe)
       - overlays em scenes/<lang>/ (a partir do roteiro traduzido)
       - narration (Edge-TTS; pulada se timing + mp3s ja existem)
       - subtitles .srt (pulada se existe)
       - timeline -> mix -> compose -> preprocess -> render
       - renomeia output/<slug>.mp4 -> output/<slug>_<lang>.mp4

Uso:
  python scripts/gerar_capitulo_trilinguo.py --prompt "Luna e Frida conhecem um parque de diversoes feito so para animais"
  python scripts/gerar_capitulo_trilinguo.py --slug luna-e-frida-conhecem-um-parque-de-diver --only-lang es
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from pipeline import (SCRIPTS, copiar_para_projeto, escolher_musica_banco,
                      listar_musicas_banco, load_json, slugify)
from translate_script import translate_script

IDIOMAS = ["pt", "en", "es"]


def run(cmd, label):
    print(f"== {label}", flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"{label} falhou com rc={r.returncode}")
    return r


def trava(script: str, *extra, label: str = ""):
    """Roda uma trava (check_*.py). Se falhar, ABORTA o capitulo antes de gastar
    tempo/dinheiro gerando ou renderizando video errado (CONTRATO.md 5.8)."""
    cmd = [sys.executable, str(HERE / script), *[str(x) for x in extra]]
    print(f"== TRAVA: {label or script}", flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("\n" + "!" * 70)
        print(f"ABORTADO pela trava: {label or script}")
        print("Corrija o problema acima antes de continuar. Nao renderize e nao")
        print("publique video com imagem repetida (CONTRATO.md 5.8).")
        print("!" * 70, flush=True)
        raise RuntimeError(f"trava falhou: {script}")


def jpg_ok(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


# ---------------------------------------------------------------------------
# Fases compartilhadas (geradas UMA vez, reaproveitadas pelos 3 idiomas)
# ---------------------------------------------------------------------------

def fase_script(args, p_dir, prompt):
    script_path = p_dir / "artifacts" / "script.json"
    if script_path.exists():
        print("== FASE script: ja existe, reaproveitando", flush=True)
        return
    run([sys.executable, str(SCRIPTS["script_from_prompt"]),
         "--prompt", prompt,
         "--out", str(script_path)],
        "FASE script: roteiro via Gemini WEB")


def fase_scenes(args, p_dir):
    scenes_json = p_dir / "artifacts" / "scenes.json"
    prompts_json = p_dir / "artifacts" / "image_prompts.json"
    if scenes_json.exists() and prompts_json.exists():
        print("== FASE scenes: ja existe, reaproveitando", flush=True)
        return
    run([sys.executable, str(SCRIPTS["scenes_from_script"]),
         "--script", str(p_dir / "artifacts" / "script.json"),
         "--scenes-out", str(scenes_json),
         "--prompts-out", str(prompts_json)],
        "FASE scenes: cenas + prompts de imagem")


def _ref_image_para(out_dir: Path, ordem: list, idx: int) -> str:
    """Continuidade: ultima imagem ja gerada (anterior na ordem) como base."""
    for j in range(idx - 1, -1, -1):
        cand = out_dir / (ordem[j] + ".jpg")
        if jpg_ok(cand):
            return str(cand)
    return ""


def _gerar_via_flow(nome, prompt_texto, out_dir, args, p_dir, ref_image):
    """Chama flow_fetch.py (Google Flow, gerador oficial). Sem fallback Gemini:
    o Gemini nao tem os modelos de Frida e Luna e gerava cachorros aleatorios."""
    cmd = [sys.executable, str(SCRIPTS["flow_fetch"]),
           "--kind", "image",
           "--prompt", prompt_texto,
           "--name", nome,
           "--project-dir", str(p_dir),
           "--out-dir", str(out_dir),
           "--wait", str(args.wait),
           "--pause", str(args.pause),
           "--skip-confirm"]
    if ref_image:
        cmd += ["--ref-image", ref_image]
    r = subprocess.run(cmd)
    size = (out_dir / (nome + ".jpg")).stat().st_size \
        if (out_dir / (nome + ".jpg")).exists() else 0
    return r.returncode, nome, size


def fase_images(args, p_dir):
    prompts_json = p_dir / "artifacts" / "image_prompts.json"
    out_dir = p_dir / "assets" / "images" / "gemini" / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts = load_json(prompts_json)
    ordem = [k for k in prompts.keys() if not k.startswith("_")]
    faltando = [n for n in ordem if not jpg_ok(out_dir / (n + ".jpg"))]

    if not faltando:
        print(f"== FASE images: todas as {len(ordem)} imagens ja existem, "
              f"reaproveitando (nada sera gerado de novo)", flush=True)
        return

    print(f"== FASE images: {len(faltando)} imagem(ns) faltando "
          f"de {len(ordem)} (Google Flow; sem fallback Gemini)", flush=True)
    for j, nome in enumerate(ordem):
        jpg = out_dir / (nome + ".jpg")
        if jpg_ok(jpg):
            continue
        ref = _ref_image_para(out_dir, ordem, j)
        ref_txt = Path(ref).name if ref else "personagens do Flow"
        print(f"== IMAGEM: {nome} (referencia: {ref_txt})", flush=True)
        rc, name, size = _gerar_via_flow(nome, prompts.get(nome, ""), out_dir,
                                         args, p_dir, ref)
        if rc != 0 or size == 0:
            print(f"  [{name}] FALHA no Flow (rc={rc} bytes={size})", flush=True)

    # quarentena: ate 4 loops, sempre pelo Flow
    quarantine = [n for n in ordem if not jpg_ok(out_dir / (n + ".jpg"))]
    tentativa = 1
    while quarantine and tentativa <= 4:
        print(f"== QUARENTENA loop {tentativa}/4: {len(quarantine)} imagem(ns)",
              flush=True)
        ainda_falham = []
        for nome in quarantine:
            ref = _ref_image_para(out_dir, ordem, ordem.index(nome))
            rc, name, size = _gerar_via_flow(nome, prompts.get(nome, ""), out_dir,
                                             args, p_dir, ref)
            if not (rc == 0 and jpg_ok(out_dir / (nome + ".jpg"))):
                ainda_falham.append(nome)
        quarantine = ainda_falham
        tentativa += 1

    if quarantine:
        print("\n" + "!" * 70)
        print("NAO CONSEGUI GERAR NO GOOGLE FLOW (como voce pediu, NAO usei o")
        print("Gemini para imagem - ele geraria cachorros aleatorios).")
        print("Abra o Google Flow no Chrome (remote debugging) e rode de novo;")
        print("o script retoma exatamente daqui, reaproveitando o que ja existe.")
        print("Faltando: " + ", ".join(quarantine))
        print("!" * 70, flush=True)
        raise RuntimeError(f"imagens faltando no Flow: {quarantine}")

    print(f"== FASE images: {len(ordem)}/{len(ordem)} imagens OK", flush=True)


def fase_music(args, p_dir, prompt):
    """Trilha compartilhada. Ordem oficial do pipeline:
    banco local -> Gemini Web -> procedural. Pula se bgm ja existe."""
    bgm = p_dir / "assets" / "audio" / "gemini" / "bgm_gemini.wav"
    bgm_proc = p_dir / "assets" / "audio" / "music" / "bgm_procedural.wav"
    if jpg_ok(bgm) or jpg_ok(bgm_proc):
        print("== FASE music: trilha ja existe, reaproveitando "
              f"({bgm.name if jpg_ok(bgm) else bgm_proc.name})", flush=True)
        return

    print("== FASE music: trilha sonora (compartilhada pelos 3 idiomas)",
          flush=True)
    # 1) banco local de musicas (rotacao sem repetir)
    musicas = listar_musicas_banco()
    if musicas:
        escolhida = escolher_musica_banco(prompt, p_dir.name)
        if escolhida:
            try:
                destino = copiar_para_projeto(
                    Path(escolhida), p_dir / "assets" / "audio",
                    f"{p_dir.name}_musica{Path(escolhida).suffix}")
                destino_final = p_dir / "assets" / "audio" / "gemini" / "bgm_gemini.wav"
                destino_final.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(destino, destino_final)
                print(f"== FASE music: trilha do banco local ({Path(escolhida).name})",
                      flush=True)
                return
            except Exception as e:
                print(f"== FASE music: falhou ao copiar do banco ({e})", flush=True)

    # 2) Gemini Web
    r = subprocess.run([sys.executable, str(SCRIPTS["fetch_music"]),
                        "--proj", str(p_dir),
                        "--prompt", prompt,
                        "--wait", str(args.wait)])
    if r.returncode == 0 and jpg_ok(bgm):
        return

    # 3) procedural local (sempre disponivel)
    print("== FASE music: Gemini/banco indisponivel; trilha procedural local",
          flush=True)
    run([sys.executable, str(HERE / "gen_music_procedural.py"),
         "--proj", str(p_dir)], "FASE music: procedural (local)")


# ---------------------------------------------------------------------------
# Fases por idioma (traducao + overlays + narracao + montagem + render)
# ---------------------------------------------------------------------------

def garantir_script_lang(p_dir, lang, args):
    """Traduz artifacts/script.json -> artifacts/script_<lang>.json (uma vez).
    Reaproveita a traducao existente - NUNCA regera."""
    if lang == "pt":
        return p_dir / "artifacts" / "script.json"
    script_lang = p_dir / "artifacts" / f"script_{lang}.json"
    if script_lang.exists():
        print(f"== TRADUCAO[{lang}]: script_{lang}.json ja existe, "
              f"reaproveitando", flush=True)
        return script_lang
    print(f"== TRADUCAO[{lang}]: traduzindo roteiro (Gemini WEB, so o texto; "
          f"imagens/cenas nao mudam)", flush=True)
    translate_script(
        p_dir / "artifacts" / "script.json", [lang], p_dir / "artifacts",
        topic=load_json(p_dir / "artifacts" / "script.json").get("title", ""),
        wait_s=int(getattr(args, "wait", 120) or 120),
    )
    if not script_lang.exists():
        raise RuntimeError(f"Nao foi possivel gerar script_{lang}.json")
    return script_lang


def garantir_overlays(p_dir, lang, script_lang):
    """Overlays por idioma em scenes/<lang>/ (texto de abertura no idioma do
    video). Sobrescreve apenas quando faltam (local e instantaneo)."""
    out_dir = p_dir / "scenes" / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    intro = out_dir / "s0.html"
    if jpg_ok(intro) and intro.stat().st_size > 0:
        print(f"== OVERLAYS[{lang}]: ja existem em scenes/{lang}/", flush=True)
        return out_dir
    run([sys.executable, str(SCRIPTS["scene_htmls"]),
         "--script", str(script_lang),
         "--scenes", str(p_dir / "artifacts" / "scenes.json"),
         "--out-dir", str(out_dir),
         "--lang", lang],
        f"FASE overlays[{lang}]: textos de tela em {lang}")
    return out_dir


def secao_ids(p_dir):
    d = load_json(p_dir / "artifacts" / "scenes.json")
    return [k for k in d.keys() if not k.startswith("_")]


def garantir_narracao(args, p_dir, lang, script_lang):
    """Narração Edge-TTS por idioma. Pula se timing + todos os mp3 existem."""
    timing = p_dir / "artifacts" / f"narration_timing_{lang}.json"
    out_dir = p_dir / "assets" / "audio" / "narration" / lang
    ids = secao_ids(p_dir)
    if timing.exists() and all((out_dir / f"{i}.mp3").exists() for i in ids):
        print(f"== NARRACAO[{lang}]: ja existe (timing + {len(ids)} mp3), "
              f"reaproveitando", flush=True)
        return

    print(f"== NARRACAO[{lang}]: gerando narração (Edge-TTS local)", flush=True)
    voice = {"pt": "pt-BR-ThalitaNeural", "en": "en-US-AriaNeural",
             "es": "es-ES-ElviraNeural"}[lang]
    run([sys.executable, str(SCRIPTS["gen_narration"]),
         "--proj", str(p_dir),
         "--lang", lang,
         "--script", str(script_lang),
         "--voice", voice,
         "--rate", "+0%",
         "--pitch", "+0Hz",
         "--workers", str(args.workers)],
        f"FASE narration[{lang}]: Edge-TTS local")


def garantir_legendas(args, p_dir, lang, script_lang):
    out_srt = p_dir / "assets" / "subtitles" / lang / f"{p_dir.name}.srt"
    if out_srt.exists() and out_srt.stat().st_size > 0:
        print(f"== LEGENDAS[{lang}]: ja existe ({out_srt.name})", flush=True)
        return out_srt
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(HERE / "gen_subtitles.py"),
         "--script", str(script_lang),
         "--timing", str(p_dir / "artifacts" / f"narration_timing_{lang}.json"),
         "--out", str(out_srt),
         "--lang", lang,
         "--gap", str(args.gap)],
        f"FASE subtitles[{lang}]: {out_srt.name}")
    return out_srt


def fase_para_idioma(args, p_dir, lang):
    """Tradução -> overlays -> narração -> legendas -> timeline -> mix ->
    compose -> preprocess -> render (reaproveita tudo que já existe)."""
    print(f"\n{'='*60}\nIDIOMA {lang.upper()}\n{'='*60}", flush=True)

    # Video final deste idioma ja existe: reaproveita (nao re-renderiza).
    video_pronto = p_dir / "output" / f"{p_dir.name}_{lang}.mp4"
    if video_pronto.exists() and video_pronto.stat().st_size > 0:
        print(f"== VIDEO[{lang}]: ja existe ({video_pronto.name}), "
              f"reaproveitando (nada sera re-renderizado)", flush=True)
        return

    script_lang = garantir_script_lang(p_dir, lang, args)
    scenes_dir_lang = garantir_overlays(p_dir, lang, script_lang)
    garantir_narracao(args, p_dir, lang, script_lang)
    garantir_legendas(args, p_dir, lang, script_lang)

    run([sys.executable, str(SCRIPTS["build_timeline"]),
         "--proj", str(p_dir), "--lang", lang],
        f"FASE timeline[{lang}]")

    mix_cmd = [sys.executable, str(SCRIPTS["mix_audio"]),
               "--proj", str(p_dir), "--lang", lang,
               "--hf-dir", str(ROOT / "hyperframes-workspace")]
    if args.provider:
        mix_cmd += ["--provider", args.provider]
    if args.gain is not None:
        mix_cmd += ["--gain", str(args.gain)]
    run(mix_cmd, f"FASE mix[{lang}]")

    run([sys.executable, str(SCRIPTS["build_composition"]),
         "--timeline", str(p_dir / "artifacts" / "timeline.json"),
         "--scenes", str(p_dir / "artifacts" / "scenes.json"),
         "--scenes-dir", str(scenes_dir_lang),
         "--proj", str(p_dir),
         "--out", str(p_dir / "composition.html"),
         "--lang", lang],
        f"FASE compose[{lang}]")

    run([sys.executable, str(SCRIPTS["preprocess_images"]),
         "--proj", str(p_dir),
         "--scenes", str(p_dir / "artifacts" / "scenes.json"),
         "--hf-dir", str(ROOT / "hyperframes-workspace")],
        f"FASE preprocess[{lang}]")

    render_cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File",
                  str(HERE / "render.ps1"),
                  "-ProjectDir", str(p_dir),
                  "-Slug", p_dir.name,
                  "-CompFile", str(p_dir / "composition.html"),
                  "-MixFile", str(p_dir / "assets" / "audio" / "final_mix.m4a")]
    if args.skip_check:
        render_cmd.append("-SkipCheck")
    run(render_cmd, f"FASE render[{lang}]")

    # output/<slug>.mp4 -> output/<slug>_<lang>.mp4
    video_gen = p_dir / "output" / f"{p_dir.name}.mp4"
    video_lang = p_dir / "output" / f"{p_dir.name}_{lang}.mp4"
    if video_gen.exists():
        if video_lang.exists():
            video_lang.unlink()
        shutil.move(str(video_gen), str(video_lang))
        print(f"== Video {lang.upper()}: {video_lang.name}", flush=True)
    else:
        print(f"== AVISO: video final nao encontrado em {video_gen}", flush=True)

    if args.burn_subtitles:
        srt = p_dir / "assets" / "subtitles" / lang / f"{p_dir.name}.srt"
        if srt.exists() and video_lang.exists():
            burned = p_dir / "output" / f"{p_dir.name}_{lang}_legendado.mp4"
            cfg = load_json(HERE / "config.json")
            ff = str(Path(cfg.get("ffmpeg_dir", str(ROOT / "ffmpeg" / "bin"))) / "ffmpeg.exe")
            run([ff, "-y", "-i", str(video_lang), "-vf",
                 f"subtitles='{srt}':force_style='FontSize=24,PrimaryColour=&H00FFFF,"
                 f"OutlineColour=&H000000,Outline=2,Shadow=1,MarginV=40'",
                 "-c:a", "copy", str(burned)],
                f"FASE render[{lang}]: queimar legendas")


def main():
    ap = argparse.ArgumentParser(
        description="Gera um capitulo em PT/EN/ES reaproveitando artefatos")
    ap.add_argument("--prompt", required=True, help="Assunto/tema do video")
    ap.add_argument("--slug", default=None, help="Nome da pasta do projeto")
    ap.add_argument("--wait", type=int, default=420,
                    help="Espera maxima pelo Gemini Web/Flow")
    ap.add_argument("--pause", type=int, default=8,
                    help="Pausa entre chamadas ao Gemini Web/Flow")
    ap.add_argument("--workers", type=int, default=4,
                    help="Workers da narracao")
    ap.add_argument("--gap", type=float, default=0.6,
                    help="Gap entre legendas (segundos)")
    ap.add_argument("--provider", default=None,
                    help="Origem da trilha na mixagem (gemini/procedural)")
    ap.add_argument("--gain", type=float, default=None, help="Ganho da mixagem")
    ap.add_argument("--skip-check", action="store_true",
                    help="Pula o check do HyperFrames no render")
    ap.add_argument("--burn-subtitles", action="store_true",
                    help="Queima legendas no video final")
    ap.add_argument("--only-lang", default="",
                    help="So gerar esse idioma (pt,en ou es)")
    args = ap.parse_args()

    prompt = args.prompt
    slug = args.slug or slugify(prompt)
    p_dir = ROOT / "projects" / slug

    print("=" * 70)
    print(f"CAPITULO TRILINGUE: {prompt}")
    print(f"Slug: {slug}")
    print(f"Projeto: {p_dir}")
    print("=" * 70, flush=True)

    # Compartilhado (gerado uma vez; pula o que ja existe)
    fase_script(args, p_dir, prompt)
    fase_scenes(args, p_dir)
    # Trava 1: prompt nao pode mandar copiar a referencia (bug §58.6).
    trava("check_prompt_repeticao.py", "--slug", slug, "--strict",
          label="prompt anti-repeticao")
    fase_images(args, p_dir)
    # Trava 2: nenhuma imagem pode ser a mesma figura de outra cena.
    trava("check_imagens_repetidas.py", "--slug", slug,
          label="imagens diferentes entre si")
    fase_music(args, p_dir, prompt)

    # Por idioma (traducao/overlays/narracao/legendas/montagem/render)
    idiomas = [args.only_lang] if args.only_lang else IDIOMAS
    for lang in idiomas:
        lang = lang.strip().lower()
        if lang not in IDIOMAS:
            print(f"AVISO: idioma '{lang}' nao suportado. Use: pt, en, es",
                  flush=True)
            continue
        fase_para_idioma(args, p_dir, lang)

    print("\n" + "=" * 70)
    print(f"CAPITULO CONCLUIDO: {prompt}")
    print("=" * 70, flush=True)
    for lang in idiomas:
        lang = lang.strip().lower()
        video = p_dir / "output" / f"{slug}_{lang}.mp4"
        if video.exists():
            print(f"  OK {lang.upper()}: {video} ({video.stat().st_size / 1e6:.1f} MB)",
                  flush=True)
        else:
            print(f"  FALTA {lang.upper()}: {video}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
