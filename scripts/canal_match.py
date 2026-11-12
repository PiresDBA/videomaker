# -*- coding: utf-8 -*-
"""Casa video do YouTube <-> projeto local.

O titulo do YouTube quase nunca e igual ao titulo do roteiro, entao o casamento
principal e por CONTEUDO: a descricao do video contem o enredo do roteiro.
Comparamos os tokens raros da descricao com os do roteiro (indice de contencao)
e aceitamos acima de um limiar (padrao 0.50). Casamento por titulo normalizado
continua como atalho.

Usado por:
  - scripts/upload_por_idioma.py   (nao subir duplicado; achar copia no canal PT)
  - scripts/relatorio_youtube.py   (o que esta publicado de verdade)
"""
import json
import re
import unicodedata
from pathlib import Path

STOPWORDS = {
    "the", "and", "that", "this", "with", "para", "com", "uma", "voce", "você",
    "ela", "ele", "dos", "das", "por", "que", "nao", "não", "mais", "como", "seu",
    "sua", "mas", "foi", "era", "tem", "you", "are", "was", "his", "her", "is",
    "of", "to", "in", "on", "it", "as", "os", "um", "em", "no", "na", "nos",
}


def _fold(s):
    t = unicodedata.normalize("NFKD", s or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def tokens(text):
    return {w for w in re.split(r"[^a-z0-9]+", _fold(text))
            if len(w) > 3 and w not in STOPWORDS}


def norm(text):
    return " ".join(_fold(text).split())


def perfis_projetos(base):
    """{slug: {'pt': tokens, 'en': tokens, 'es': tokens, 'titulos': {...}}}"""
    base = Path(base)
    perfis = {}
    for proj in sorted(base.iterdir()):
        if not proj.is_dir():
            continue
        art = proj / "artifacts"
        dados = {}
        for lang, nome in (("pt", "script.json"),
                           ("en", "script_en.json"),
                           ("es", "script_es.json")):
            p = art / nome
            if not p.is_file():
                continue
            try:
                s = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            partes = [s.get("title", "")]
            for sec in s.get("sections", []):
                if sec.get("id") in ("s_intro", "s0", "s_outro"):
                    continue
                partes.append(sec.get("text", ""))
            dados[lang] = {
                "tokens": tokens(" ".join(partes)),
                "titulo": norm(s.get("title", "")),
            }
        if dados:
            perfis[proj.name] = dados
    return perfis


def melhor_projeto(descricao, perfis, lang=None, limiar=0.50):
    """Devolve (slug, score) do projeto cujo roteiro melhor explica a descricao."""
    t = tokens(descricao)
    if not t:
        return None, 0.0
    melhor, score = None, 0.0
    for slug, langs in perfis.items():
        if lang and lang not in langs:
            continue
        pt = langs[lang]["tokens"] if lang else None
        if not pt:
            # Sem roteiro no idioma: tenta qualquer idioma
            pt = set()
            for d in langs.values():
                pt |= d["tokens"]
        if not pt:
            continue
        s = len(t & pt) / float(len(pt))
        if s > score:
            melhor, score = slug, s
    return (melhor, score) if score >= limiar else (None, score)


def duracao_mp4(mp4):
    """Duracao do arquivo local em segundos (0.0 se falhar)."""
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp4)],
            capture_output=True, text=True, timeout=60)
        return float((r.stdout or "0").strip() or 0)
    except Exception:
        return 0.0


def casar_por_duracao(videos, lang, duracao, tolerancia=2.0):
    """Videos do canal do idioma cuja duracao bate com o MP4 local.

    E o casamento mais confiavel: nao depende de titulo nem de descricao
    (que o dono do canal pode ter editado depois do upload).
    """
    if not duracao:
        return []
    achados = []
    for v in videos:
        dl = (v.get("default_language") or "")
        if not dl.startswith(lang):
            continue
        if abs(float(v.get("duration_s") or 0) - duracao) <= tolerancia:
            achados.append(v)
    return achados


def mapa_de_videos(videos, base, lang, limiar=0.50):
    """Casa uma lista de videos do canal com projetos.

    videos: saida de listar_canal.list_videos (dicts com title, description,
            default_language, video_id, views).
    Retorna {(slug, lang): {'video_id':..., 'views':..., 'score':..., 'titulo':...}}
    """
    perfis = perfis_projetos(base)
    # Atalho por titulo normalizado (alto grau de confianca)
    por_titulo = {}
    for slug, langs in perfis.items():
        for l, d in langs.items():
            if d["titulo"]:
                por_titulo.setdefault((l, d["titulo"]), slug)

    mapa = {}
    for v in videos:
        dl = (v.get("default_language") or "")
        if lang == "pt":
            if not dl.startswith("pt"):
                continue
        elif not dl.startswith(lang):
            continue

        slug = por_titulo.get((lang, norm(v.get("title", ""))))
        score = 1.0 if slug else 0.0
        if not slug:
            slug, score = melhor_projeto(v.get("description", ""), perfis, lang, limiar)
        if not slug:
            continue

        atual = mapa.get((slug, lang))
        # Se o projeto ja apareceu, guarda o video com mais views (o "principal")
        if atual is None or int(v.get("views", 0)) > atual["views"]:
            mapa[(slug, lang)] = {
                "video_id": v["video_id"],
                "views": int(v.get("views", 0)),
                "score": round(score, 3),
                "titulo": v.get("title", ""),
            }
    return mapa
