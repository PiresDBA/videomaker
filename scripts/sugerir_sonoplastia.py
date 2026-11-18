# -*- coding: utf-8 -*-
"""sugerir_sonoplastia.py - MAPA DE SONOPLASTIA (sound design).

Cruza tres fontes para sugerir ONDE e QUAL som inserir:
  1. Segmentos de voz do earshot (relatorio_earshot.txt) -> pausas naturais
  2. Transcricao palavra-a-palavra (Whisper) -> palavras-chave / Foley
  3. video_clips.json -> entradas dos 5 clipes de video

Gera artifacts/auditoria/mapa_sonoplastia.txt com entradas:
  tempo, tipo, som sugerido, intensidade, motivo.

Regra: o som tem que casar com o que esta sendo FALADO e VISTO no mesmo
instante (REGRA DE OURO §65 estendida ao audio).
"""
from __future__ import annotations
import json, re, unicodedata
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
A = P / "artifacts"
AUD = A / "auditoria"
REL = Path(r"C:\videomaker\relatorio_earshot.txt")
OUT = AUD / "mapa_sonoplastia.txt"
DUR_VIDEO = 934.87  # duracao do MP4 final (apos corte do preto)

# ------------------------------------------------------------------ carregar
tr = json.load(open(AUD / "transcricao.json", encoding="utf-8"))
vc = json.load(open(A / "video_clips.json", encoding="utf-8"))
txt = REL.read_text(encoding="utf-8")
voz = [(float(m.group(1)), float(m.group(2)))
       for m in re.finditer(r"^\s*\d+\s+([\d.]+)\s+([\d.]+)\s+", txt, re.M)]

palavras = []
for s in tr["segments"]:
    for w in s.get("words", []):
        if w["w"].strip():
            palavras.append((w["w"].strip().lower(), float(w["s"]), float(w["e"])))


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


# pausas entre segmentos de voz. O earshot analisou o MP4 FINAL, entao seus
# tempos JA estao no cronometro do video — NAO somar +8s aqui.
gaps = []
for i in range(1, len(voz)):
    g = voz[i][0] - voz[i - 1][1]
    if 0.35 < g < 2.0:
        a, b = voz[i - 1][1], voz[i][0]
        if b <= DUR_VIDEO:  # descarta pausas fora do video cortado
            gaps.append((a, b, g))

# ------------------------------------------------------- regras de Foley
# (padrao, som, int, motivo) - casado com PALAVRA falada
FOLEY = [
    (r"espirr", "espirro cartoon (atchim!) + pequeno eco", "alto", "espirro da Frida"),
    (r"ossinh?o|osso voador", "osso passando assobiando + 'plop' na grama", "medio", "fala de ossinhos"),
    (r"biscoinho|biscoito|racao|comidinha|comida|almoco|petisco", "tin-tin de tigela + mastigada crocante", "baixo", "fala de comida"),
    (r"bolinha|bola de tenis|bola", "quique de bola de tenis + 'boing' macio", "medio", "fala da bolinha"),
    (r"passarinho|passaro|pombo|pomb", "piao curto + batida de asas", "baixo", "fala de passaro/pombo"),
    (r"abelha|\bmel\b", "zumbido de abelha passando", "baixo", "fala de abelha"),
    (r"carro|camiao|buzina|transito", "buzina distante + passada de carro", "baixo", "fala de carros"),
    (r"chuva|tempestade", "chuva leve + trovão distante", "medio", "fala de chuva"),
    (r"sono|dormir|bocejo|boceja|sonolent", "bocejo suave + 'zzz' ambiental", "baixo", "fala de sono"),
    (r"cant|musica|cantando", "pequeno ritornello musical alegre (xilofone)", "medio", "fala de cantar"),
    (r"coracao|amor|carinho|abra.o|beijo", "som de coração batendo + 'boop' doce", "baixo", "fala de carinho"),
    (r"magia|magico|poeira|poirinha|estrelinha|brilh", "shimmer mágico (sino + brilho ascendente)", "alto", "fala de magia/poeira"),
    (r"espanto|susto|susto do mundo|uau|nossa", "whoosh de susto + 'pop' cartoon", "medio", "reação de espanto"),
    (r"risadinha|rir|riso|hahaha", "risadinha curta (child-like giggle)", "baixo", "fala de rir"),
    (r"pata|patinha|passo|caminh", "passos macios de patinhas no piso", "baixo", "fala de patas/caminhada"),
]

itens = []

# 1) Foley por palavra-chave (pega a PRIMEIRA ocorrencia de cada regra)
for padrao, som, inten, motivo in FOLEY:
    hit = None
    for w, s, e in palavras:
        if re.search(padrao, norm(w)):
            hit = (s + 8.0, w, e + 8.0)
            break
    if hit:
        itens.append({
            "t": hit[0], "tipo": "FOLEY", "som": som, "int": inten,
            "motivo": f"'{hit[1]}' a {hit[0]:.1f}s - {motivo}",
        })

# 2) Transicoes nas maiores pausas (whoosh suave)
for a, b, g in sorted(gaps, key=lambda x: -x[2])[:12]:
    if g >= 0.6:
        itens.append({
            "t": (a + b) / 2, "tipo": "TRANSICAO", "som": "whoosh suave + leve 'tick' (transição de cena)",
            "int": "baixo" if g < 0.9 else "medio",
            "motivo": f"pausa natural de {g:.2f}s ({a:.1f}-{b:.1f}s)",
        })

# 3) Entradas dos clipes de video
clip_info = [
    ("intro", "intro-nova-8s.mp4", 0.0, "swish de abertura + acorde musical brilhante", "alto"),
    ("meio", None, None, "impacto macio de bola + risadinha", "medio"),
    ("meio3", None, None, "shimmer mágico ascendente (poeira dourada)", "alto"),
    ("meio2", None, None, "osso assobiando + 'plop' na grama", "alto"),
    ("pre_final", None, None, "explosão de confete + fanfarra curta", "alto"),
    ("outro", None, None, "campainha de subscribe + 'pop' amigável", "alto"),
]
# tempos reais dos clipes na composicao (calculados via timeline + offset)
tl = json.load(open(A / "timeline.json", encoding="utf-8"))
INTRO = float(vc.get("intro_dur", 8.0))
starts = {}
for sec in tl["timeline"]:
    starts[sec["id"]] = sec["start"] + INTRO
s1 = starts.get("s1", 23.0)
s12 = starts.get("s12", 0.0)
meio = vc.get("meio", {})
meio3 = vc.get("meio3", {})
meio2 = vc.get("meio2", {})
clip_times = {
    "intro": 0.0,
    "meio": s1 + float(meio.get("offset", 0.0)),
    "meio3": s1 + float(meio3.get("offset", 0.0)),
    "meio2": s12,
    "pre_final": None, "outro": None,
}
# pre_final/outro vem do build_composition (tempos fixos conhecidos da ficha)
clip_times["pre_final"] = 915.19
clip_times["outro"] = 929.90

for key, fname, _, som, inten in clip_info:
    t = clip_times.get(key)
    if t is None:
        continue
    f = fname or (vc.get(key, {}).get("file") if isinstance(vc.get(key), dict) else vc.get(key, ""))
    itens.append({
        "t": t, "tipo": "CLIPE", "som": som, "int": inten,
        "motivo": f"entrada do clipe {key} ({f})",
    })

# 4) Abertura e CTA
itens += [
    {"t": 0.3, "tipo": "ABERTURA", "som": "acorde de introdução alegre + whoosh", "int": "alto",
     "motivo": "gancho inicial (capa 0-8s)"},
    {"t": 930.4, "tipo": "CTA", "som": "campainha de notificação + 'like' pop", "int": "alto",
     "motivo": "tela final 'Inscreva-se' (929.9s)"},
]

# remove itens fora da duracao do video e ordena/deduplica
itens = [it for it in itens if 0 <= it["t"] <= DUR_VIDEO]
itens.sort(key=lambda x: (x["t"], x["tipo"]))
vistos = set()
unicos = []
for it in itens:
    k = round(it["t"], 1)
    if k in vistos:
        continue
    vistos.add(k)
    unicos.append(it)

# ------------------------------------------------------------------ relatorio
L = []
L.append("=" * 100)
L.append("MAPA DE SONOPLASTIA (SOUND DESIGN) - e se os cachorros pudessem falar por um dia?")
L.append("=" * 100)
L.append(f"Narracao: {tr['duration']:.2f}s | Video final: {DUR_VIDEO:.2f}s (capa +8s)")
L.append(f"Voz detectada (earshot): {len(voz)} segmentos | Pausas uteis: {len(gaps)}")
L.append(f"Sugestoes de insercao: {len(unicos)}")
L.append("Tempos abaixo ja estao no CRONOMETRO DO VIDEO (inclui +8s de capa).")
L.append("-" * 100)
L.append(f"{'TEMPO':>8}  {'TIPO':>9}  {'INT':>6}  SOM / MOTIVO")
L.append("-" * 100)
for it in unicos:
    mm, ss = divmod(it["t"], 60)
    L.append(f"{int(mm):>3d}:{ss:05.2f}  {it['tipo']:>9}  {it['int']:>6}  {it['som']}")
    L.append(f"{'':>8}  {'':>9}  {'':>6}  -> {it['motivo']}")
L.append("=" * 100)
L.append("REGRAS DE OURO APLICADAS:")
L.append("  - Som casa com o que e FALADO e VISTO no mesmo instante (§65).")
L.append("  - Foley discreto (baixo/medio) sob a narração; efeitos fortes só em clipes/pausas.")
L.append("  - Nunca mascarar a voz: usar sidechain/ducking (o mix ja tem sidechaincompress).")
L.append("  - Volumes sugeridos sao relativos a narração; mixar com -18 a -24 LUFS para efeitos.")
L.append("=" * 100)

relatorio = "\n".join(L)
OUT.write_text(relatorio, encoding="utf-8")
print(relatorio[:6000])
print("\n... completo:", OUT)
