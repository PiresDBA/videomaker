# -*- coding: utf-8 -*-
"""
Gera a narracao com Edge-TTS (100% local, sem API, sem tokens, CPU).
Cada secao vira um MP3 em assets/audio/narration/<lang>/sN.mp3 e grava
artifacts/narration_timing_<lang>.json com a duracao real de cada um.

Quando --lang for diferente de pt, usa o arquivo artifacts/script_<lang>.json
(gerado por translate_script.py) como fonte do texto.

IMPORTANTE: texto PURO (sem SSML). SSML customizado faz o servico ler as
tags em voz alta ("speak version 1.0 xml lang...") no inicio de cada bloco.
A energia vem de rate/pitch + frases do roteiro. Risadas escritas
("Hahaha!") sao removidas do texto: soam falsas/forcadas na voz neural.

TODOS OS TEXTOS SAO PROCESSADOS EM UTF-8. Caracteres especiais (ç, ã, õ, á,
é, í, ó, ú, â, ê, ô) sao preservados para a voz neural ler corretamente.

Vozes padrao por idioma:
  pt: pt-BR-ThalitaNeural (rate +6%, pitch +8Hz)
  en: en-US-AriaNeural    (rate +0%, pitch +0Hz)
  es: es-ES-ElviraNeural  (rate +0%, pitch +0Hz)

Uso:
  python scripts/gen_narration_edge.py                                        # pt, padrao
  python scripts/gen_narration_edge.py --lang en --voice en-US-AriaNeural     # ingles
  python scripts/gen_narration_edge.py --lang es --voice es-ES-ElviraNeural   # espanhol
  python scripts/gen_narration_edge.py --only s1,s4 --workers 4 --proj <dir>
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from narration_contract import apply_contract, validate_contract

HERE = Path(__file__).resolve().parent

# Risadas escritas ("Hahaha!", "ha ha ha", "HAHAH", "rsrsrs", "kkkkk", "he he") ficam forçadas na voz:
# removidas do texto antes do TTS. A energia vem de rate/pitch + frases.
LAUGH_RE = re.compile(r"(?i)\b(?:ha[\s\-!]*|he[\s\-!]*|hi[\s\-!]*|ho[\s\-!]*|rs[\s\-!]*|kk[\s\-!]*){2,}[!\.,]?\s*")

# Substituicoes de palavra para narracao (evitar TTS ler "gatinha" para cadelas).
PRONUNCIATION_MAP = [
    (r"\bgatinha\b", "cachorrinha"),
    (r"\bgatinho\b", "cachorro"),
    (r"\bgatos\b", "cachorros"),
    (r"\bgata\b", "cadela"),
    (r"\bgato\b", "cachorro"),
]

# Vozes padrao por idioma quando --voice nao e informado.
DEFAULT_VOICES = {
    "pt": "pt-BR-ThalitaNeural",
    "en": "en-US-AriaNeural",
    "es": "es-ES-ElviraNeural",
}
DEFAULT_RATES = {
    "pt": "+6%",
    "en": "+0%",
    "es": "+0%",
}
DEFAULT_PITCHES = {
    "pt": "+8Hz",
    "en": "+0Hz",
    "es": "+0Hz",
}


def limpar_texto_para_tts(text: str) -> str:
    """Limpa o texto para o TTS sem remover caracteres especiais do portugues.
    
    Remove apenas risadas escritas e parenteses orfaos. Mantem acentos, cedilha
    e todos os caracteres latinos para o Edge-TTS ler corretamente.
    """
    if not text:
        return ""
    # Normaliza espacos em branco
    text = " ".join(text.split())
    # Remove risadas escritas
    text = LAUGH_RE.sub(" ", text)
    # Remove parenteses orfaos
    text = re.sub(r"\(\s*\)", " ", text)
    # Normaliza espacos novamente apos substituicoes
    text = " ".join(text.split())
    return text


def aplicar_substituicoes_pronunciacao(text: str) -> str:
    """Aplica substituicoes de pronuncia (evitar TTS ler 'gatinha' para cadelas)."""
    for pat, repl in PRONUNCIATION_MAP:
        text = re.sub(pat, repl, text, flags=re.I)
    return text


def remover_espaco_antes_pontuacao(text: str) -> str:
    """Remove espaco antes de virgula, ponto, exclucao, interrogacao."""
    return re.sub(r"\s+([,\.!?])", r"\1", text)


def limpar_e_preparar_texto(text: str) -> str:
    """Pipeline completo de limpeza do texto para TTS, preservando caracteres especiais."""
    text = limpar_texto_para_tts(text)
    text = aplicar_substituicoes_pronunciacao(text)
    text = remover_espaco_antes_pontuacao(text)
    text = " ".join(text.split())
    return text


def load_json(p):
    """Carrega JSON com encoding UTF-8 explicito para preservar caracteres especiais."""
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, d):
    """Grava JSON com encoding UTF-8 explicito."""
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    ap.add_argument("--lang", default="pt", help="idioma da narracao (pt, en, es). padrao: pt")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", default=None)
    ap.add_argument("--pitch", default=None, help="ajuste de altura em Hz (ex: +8Hz)")
    ap.add_argument("--style", default=None, help="(ignorado: SSML causa jargao falado)");
    ap.add_argument("--script", default=None, help="caminho do script JSON (padrao: artifacts/script_<lang>.json)")
    ap.add_argument("--only", default=None, help="ids separados por virgula")
    ap.add_argument("--retries", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4, help="secoes em paralelo")
    args = ap.parse_args()

    lang = (args.lang or "pt").lower().strip()

    cfg = load_json(HERE / "config.json")
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    artifacts = proj / "artifacts"

    # Escolhe o arquivo de script: --script > script_<lang>.json > script.json
    if args.script:
        script_path = Path(args.script)
    elif lang != "pt" and (artifacts / f"script_{lang}.json").exists():
        script_path = artifacts / f"script_{lang}.json"
    else:
        script_path = artifacts / "script.json"
    script = load_json(script_path)

    # Contrato de abertura/encerramento: repara o roteiro antes do TTS e grava
    # de volta, para que narracao, cenas e timeline usem o mesmo texto.
    # (solo faz sentido para o script PT principal; linguas traduzidas ja estao adaptadas)
    if lang == "pt":
        script, mudancas = apply_contract(script, theme=script.get("title") or "")
        if mudancas:
            print("== CONTRATO narracao: " + "; ".join(mudancas))
            save_json(script_path, script)
        problemas = validate_contract(script)
        if problemas:
            print("== AVISO contrato de narracao:", "; ".join(problemas))

    voice = args.voice or DEFAULT_VOICES.get(lang, "pt-BR-ThalitaNeural")
    rate = args.rate or DEFAULT_RATES.get(lang, "+0%")
    pitch = args.pitch or DEFAULT_PITCHES.get(lang, "+0Hz")

    out = proj / "assets" / "audio" / "narration" / lang
    out.mkdir(parents=True, exist_ok=True)

    only = set(args.only.split(",")) if args.only else None

    # Cada secao do roteiro (ja com abertura s0 e agradecimento s_outro) vira
    # uma tarefa. Nao existe intro/outro "extra": o script e a fonte unica.
    tarefas = []
    for s in script["sections"]:
        sid = s["id"]
        if only and sid not in only:
            continue
        texto = s.get("text", "").strip()
        if not texto:
            continue
        tarefas.append((sid, texto))

    def gen_one(item):
        sid, texto = item
        dst = out / ("%s.mp3" % sid)
        text = limpar_e_preparar_texto(texto)
        for attempt in range(args.retries):
            try:
                async def g():
                    import edge_tts
                    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                    await comm.save(str(dst))
                asyncio.run(g())
                break
            except Exception as e:
                print("%s: erro %s (tentativa %d/%d)" % (sid, str(e)[:80], attempt + 1, args.retries))
                time.sleep(5)
        if dst.exists() and dst.stat().st_size > 1000:
            d = subprocess.run(
                [str(Path(cfg["ffmpeg_dir"]) / "ffprobe.exe"), "-v", "error",
                 "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(dst)],
                capture_output=True, text=True).stdout.strip()
            dur = float(d) if d else 0.0
            print("%-6s %7.2fs" % (sid, dur))
            return {"id": sid, "path": str(dst), "duration": round(dur, 3)}
        print("%s: FALHA ao gerar" % sid)
        return None

    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        for r in ex.map(gen_one, tarefas):
            if r:
                results.append(r)

    # Ordena conforme a ordem das secoes do roteiro (s0 primeiro, s_outro ultimo)
    ordem = [t[0] for t in tarefas]
    results.sort(key=lambda t: ordem.index(t["id"]))
    timing_path = artifacts / f"narration_timing_{lang}.json"
    save_json(timing_path, results)
    print("TOTAL %.1fs  [%s]" % (sum(t["duration"] for t in results), lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())
