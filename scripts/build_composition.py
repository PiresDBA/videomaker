# -*- coding: utf-8 -*-
"""
Monta o index.html do HyperFrames a partir de:
  - artifacts/timeline.json      (inicio/duracao reais de cada secao)
  - scripts/scenes.json          (imagens + movimento de camera por secao)
  - scripts/scenes/<secao>.html  (overlays de texto de cada secao)
  - scripts/config.json          (resolucao, caminhos)

Uso:
  python scripts/build_composition.py
  python scripts/build_composition.py --timeline artifacts/timeline.json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;background:#0A0705}
body{font-family:"Segoe UI","Trebuchet MS",sans-serif;-webkit-font-smoothing:antialiased}
#root{position:relative;width:1920px;height:1080px;overflow:hidden;background:#0A0705}
.scene{position:absolute;inset:0;overflow:hidden;background:#0A0705}
.cam{position:absolute;left:-3%;top:-3%;width:106%;height:106%;object-fit:cover;will-change:transform;transform-origin:50% 50%}
video.cam{object-fit:cover;width:106%;height:106%;left:-3%;top:-3%;position:absolute;will-change:transform;background:#000}
video.clip-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#000}
.cam-b{opacity:0}
.ov{position:absolute;inset:0;pointer-events:none}
/* Particulas: micro bolinhas de sabao subindo - da vida as imagens sem zoom */
.bubbles{position:absolute;inset:0;pointer-events:none;overflow:hidden}
.bubble{position:absolute;border-radius:50%;
  background:radial-gradient(circle at 30% 30%,rgba(255,255,255,.55) 0%,rgba(255,255,255,.10) 35%,rgba(180,220,255,.18) 70%,rgba(255,255,255,.05) 100%);
  border:1px solid rgba(255,255,255,.28);
  box-shadow:inset 0 0 6px rgba(255,255,255,.35),0 0 8px rgba(255,255,255,.12);
  opacity:0;will-change:transform,opacity}
/* Particulas tematicas (imagens PNG da BIBLIOTECA_EFEITOS) */
.particula{position:absolute;pointer-events:none;opacity:0;will-change:transform,opacity}
.part-folha{background-image:url('assets/efeitos/folha.png')}
.part-bolha{background-image:url('assets/efeitos/bolha.png')}
.part-estrela{background-image:url('assets/efeitos/estrela.png')}
.part-coracao{background-image:url('assets/efeitos/coracao.png')}
.part-abelha{background-image:url('assets/efeitos/abelha.png')}
.part-osso{background-image:url('assets/efeitos/osso.png')}
.part-zzz{background-image:url('assets/efeitos/zzz.png')}
.part-gota{background-image:url('assets/efeitos/gota.png')}
.part-passaro{background-image:url('assets/efeitos/passaro.png')}
.part-fumaca{background-image:url('assets/efeitos/fumaca.png')}
.part-racao{background-image:url('assets/efeitos/racao_bola.png')}
.part-racao2{background-image:url('assets/efeitos/racao_tri.png')}
.part-racao3{background-image:url('assets/efeitos/racao_oval.png')}
.scrim-b{background:radial-gradient(ellipse at 50% 48%,rgba(0,0,0,0) 46%,rgba(0,0,0,.40) 100%),linear-gradient(0deg,rgba(8,5,3,.88) 0%,rgba(8,5,3,.55) 24%,rgba(8,5,3,.12) 50%,rgba(8,5,3,0) 70%)}
.scrim-l{background:radial-gradient(ellipse at 50% 48%,rgba(0,0,0,0) 46%,rgba(0,0,0,.40) 100%),linear-gradient(90deg,rgba(8,5,3,.86) 0%,rgba(8,5,3,.55) 32%,rgba(8,5,3,.08) 62%,rgba(8,5,3,0) 78%)}
.scrim-t{background:radial-gradient(ellipse at 50% 48%,rgba(0,0,0,0) 46%,rgba(0,0,0,.40) 100%),linear-gradient(180deg,rgba(8,5,3,.78) 0%,rgba(8,5,3,.35) 22%,rgba(8,5,3,0) 46%)}
.scrim-c{background:radial-gradient(ellipse at 50% 52%,rgba(8,5,3,0) 30%,rgba(8,5,3,.60) 100%)}
.scrim-v{background:radial-gradient(ellipse at 50% 48%,rgba(8,5,3,0) 34%,rgba(8,5,3,.30) 62%,rgba(8,5,3,.62) 100%)}
.scrim-r{background:radial-gradient(ellipse at 50% 48%,rgba(0,0,0,0) 46%,rgba(0,0,0,.34) 100%),linear-gradient(270deg,rgba(8,5,3,.68) 0%,rgba(8,5,3,.38) 34%,rgba(8,5,3,.06) 64%,rgba(8,5,3,0) 80%)}
.grain{opacity:.055;mix-blend-mode:overlay;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E")}
.block{position:absolute;max-width:980px}
.bl{left:110px;bottom:104px}
.bl-mid{left:110px;top:50%;transform:translateY(-50%)}
.bc{left:50%;bottom:96px;transform:translateX(-50%);text-align:center}
.tc{left:50%;top:84px;transform:translateX(-50%);text-align:center}
.eyebrow{font-size:25px;font-weight:700;letter-spacing:.34em;text-transform:uppercase;color:#F0B24A;text-shadow:0 2px 18px rgba(0,0,0,.7)}
.h-xl{font-size:110px;font-weight:900;line-height:.93;letter-spacing:-.035em;color:#FFF6EA;text-shadow:0 8px 46px rgba(0,0,0,.65)}
.h-lg{font-size:82px;font-weight:900;line-height:.98;letter-spacing:-.03em;color:#FFF6EA;text-shadow:0 6px 36px rgba(0,0,0,.62)}
.h-md{font-size:58px;font-weight:900;line-height:1.02;letter-spacing:-.02em;color:#FFF6EA;text-shadow:0 4px 28px rgba(0,0,0,.6)}
.serif{font-family:Georgia,"Times New Roman",serif;font-style:italic;font-weight:400;letter-spacing:-.01em}
.gold{color:#F0B24A}
.body{font-size:33px;font-weight:600;line-height:1.36;color:rgba(255,246,234,.97);text-shadow:0 2px 18px rgba(0,0,0,.85),0 1px 3px rgba(0,0,0,.7)}
.sub{font-size:36px;font-weight:600;color:rgba(255,246,234,.95);letter-spacing:.01em;text-shadow:0 2px 20px rgba(0,0,0,.85),0 1px 3px rgba(0,0,0,.7)}
.glass{background:linear-gradient(155deg,rgba(24,16,10,.50),rgba(10,7,4,.30));border:1px solid rgba(255,246,234,.26);border-radius:26px;padding:26px 38px;box-shadow:0 22px 60px rgba(0,0,0,.34),inset 0 1px 0 rgba(255,255,255,.10);-webkit-backdrop-filter:blur(16px) saturate(120%);backdrop-filter:blur(16px) saturate(120%)}
.glass-soft{background:linear-gradient(155deg,rgba(24,16,10,.34),rgba(10,7,4,.16));border:1px solid rgba(255,246,234,.18);border-radius:26px;padding:24px 34px;-webkit-backdrop-filter:blur(10px) saturate(115%);backdrop-filter:blur(10px) saturate(115%)}
.chips{display:flex;flex-wrap:wrap;gap:14px}
.chip{display:inline-flex;align-items:center;gap:12px;padding:12px 24px;border-radius:999px;background:rgba(20,13,8,.40);border:1px solid rgba(255,246,234,.26);font-size:27px;font-weight:700;color:#FFF6EA;text-shadow:0 2px 12px rgba(0,0,0,.7);-webkit-backdrop-filter:blur(10px) saturate(120%);backdrop-filter:blur(10px) saturate(120%)}
.chip .dot{width:10px;height:10px;border-radius:50%;background:#F0B24A;flex:none}
.chip.alt .dot{background:#E87A4E}
.stat{display:flex;align-items:baseline;gap:18px}
.stat .num{font-size:104px;font-weight:900;line-height:.9;letter-spacing:-.04em;color:#F0B24A;text-shadow:0 6px 36px rgba(0,0,0,.6)}
.stat .lbl{font-size:30px;font-weight:700;line-height:1.15;color:rgba(255,246,234,.95);max-width:420px;text-shadow:0 2px 14px rgba(0,0,0,.7)}
.etym{display:flex;flex-direction:column;gap:10px}
.etym .row{display:flex;align-items:baseline;gap:20px}
.etym .word{font-size:76px;font-weight:900;letter-spacing:-.02em;color:#FFF6EA}
.etym .eq{font-size:52px;font-weight:800;color:#F0B24A}
.etym .mean{font-size:64px;font-weight:700;color:#FFF6EA}
.rank{display:flex;flex-direction:column;gap:2px}
.rank .n{font-size:132px;font-weight:900;line-height:.9;letter-spacing:-.04em;color:#FFF6EA;text-shadow:0 6px 34px rgba(0,0,0,.6)}
.rank .t{font-size:32px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:rgba(255,246,234,.9);text-shadow:0 2px 14px rgba(0,0,0,.7)}
.rank.a .n{color:#F0B24A}
.rank.b .n{color:#E87A4E}
.two{display:flex;gap:34px;align-items:flex-start}
.panel{flex:1;min-width:380px}
.panel h3{font-size:30px;font-weight:800;letter-spacing:.2em;text-transform:uppercase;margin-bottom:14px}
.panel.bad h3{color:#E87A4E}
.panel.good h3{color:#8FD06A}
.panel ul{list-style:none;display:flex;flex-direction:column;gap:9px}
.panel li{font-size:29px;font-weight:600;color:rgba(255,246,234,.95);display:flex;gap:12px;align-items:baseline}
.panel li:before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor;flex:none;opacity:.8}
.panel.bad li:before{background:#E87A4E}
.panel.good li:before{background:#8FD06A}
.clock{font-size:170px;font-weight:900;letter-spacing:-.05em;color:#FFF6EA;text-shadow:0 8px 60px rgba(0,0,0,.75)}
.whisper{font-family:Georgia,serif;font-style:italic;font-size:38px;color:rgba(255,246,234,.85);text-shadow:0 2px 20px rgba(0,0,0,.8)}
.divider{width:92px;height:5px;border-radius:3px;background:#F0B24A;margin:22px 0 20px}
.badge{display:inline-flex;align-items:center;gap:12px;padding:10px 22px;border-radius:12px;background:#F0B24A;border:1px solid #D4A327;font-size:34px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#000000}
"""

TAG_RE = re.compile(r"<[a-zA-Z][^>]*data-anim[^>]*>")
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

ANIM = {
    "rise":   {"opacity": 0, "y": 44},
    "fade":   {"opacity": 0},
    "left":   {"opacity": 0, "x": -50},
    "right":  {"opacity": 0, "x": 50},
    "scale":  {"opacity": 0, "scale": 0.86},
    "line":   {"opacity": 0, "scaleX": 0, "transformOrigin": "0% 50%"},
    "soft":   {"opacity": 0.45, "y": 8},
    "pop":    {"opacity": 0, "scale": 0.55, "y": 22},
    "bounce": {"opacity": 0, "y": 78},
    "drop":   {"opacity": 0, "y": -56},
    "swing":  {"opacity": 0, "rotation": -6, "y": 26},
    "tilt":   {"opacity": 0, "rotation": 5, "scale": 0.9},
    "zoom":   {"opacity": 0, "scale": 1.18},
}

EASE = {
    "pop":    '"back.out(2.4)"',
    "bounce": '"bounce.out"',
    "drop":   '"back.out(1.7)"',
    "swing":  '"back.out(2.0)"',
    "tilt":   '"back.out(2.2)"',
    "zoom":   '"back.out(1.5)"',
    "line":   '"power4.out"',
    "soft":   '"power1.out"',
}
# Duracoes das animacoes de texto (skills: stagger 100-200ms, hold curto,
# movimento com energia). 2026-11-16: encurtado de 0.8-0.9s para 0.45-0.6s
# porque o usuario achou as animacoes lentas.
DUR_ANIM = {
    "pop": 0.45,
    "line": 0.50,
    "bounce": 0.60,
    "zoom": 0.55,
    "swing": 0.55,
    "tilt": 0.55,
    "drop": 0.55,
    "soft": 0.60,
}
DUR_ANIM_PADRAO = 0.55


def inject_ids(html, sid):
    """Dá um id automático a cada elemento com data-anim que ainda não tem id."""
    state = {"n": 0}

    def repl(m):
        tag = m.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        if "id" in attrs:
            return tag
        state["n"] += 1
        return tag[:-1] + ' id="%s-a%d">' % (sid, state["n"])

    return TAG_RE.sub(repl, html)


def collect_anims(html, sid):
    out = []
    for tag in TAG_RE.findall(html):
        a = dict(ATTR_RE.findall(tag))
        if "id" not in a:
            continue
        out.append(a)
    return out


# Transicoes entre imagens/beats (regra cinematica: crossfade 0.5-1.0s;
# ver skills/creative/cinematic.md e skills/creative/animation-pipeline.md).
# Tipos suportados: crossfade (default), fade, zoom, slide, hard.
# 2026-11-16: duracoes encurtadas (0.9 -> 0.6s) e easing mais seco, porque o
# usuario achou as animacoes "muito devagar" (skills: TRANSITION 0.5-1.0s).
XFADE = 0.6  # crossfade entre cenas (ajustavel)
TRANSICOES = {
    "crossfade": 1.0,
    "fade": 0.7,
    "zoom": 0.75,
    "slide": 0.6,
    "hard": 0.0,
}
EASE_IMAGEM = '"power1.inOut"'   # crossfade mais suave e claro
EASE_SAIDA = '"power1.inOut"'    # saida de cena mais suave
EASE_CAMERA = '"power1.inOut"'  # camera com movimento continuo, sem overshoot final
CAM_VIBRANCI = 2.4   # amplia o deslocamento de camera (motion mais vivo)

def _video_clips_config():
    """Le artifacts/video_clips.json do projeto (via VIDEOMAKER_PROJ).

    Formato:
      {"intro":"intro_8s.mp4","intro_dur":8,
       "meio":{"scene":"s10","file":"meio_8s.mp4"},
       "outro":"subscribe_8s.mp4","outro_dur":8}
    Sem o arquivo, mantem o comportamento classico (capa/outro estaticos).
    """
    p = Path(os.environ.get("VIDEOMAKER_PROJ", "")) / "artifacts" / "video_clips.json"
    try:
        if p.exists():
            return load_json(p)
    except Exception:
        pass
    return {}


_CLIPS = _video_clips_config()
INTRO_DUR = float(_CLIPS.get("intro_dur", 4.0))   # duracao da capa
OUTRO_DUR = float(_CLIPS.get("outro_dur", 5.0))   # duracao da tela final


def _load_paineis():
    """Mapa nome->quantidade de paineis (detecta_paineis.py). Colagens nao
    recebem zoom vai-e-vem para nao cortar os paineis."""
    proj = os.environ.get("VIDEOMAKER_PROJ", "")
    p = Path(proj) / "assets" / "images" / "gemini" / "paineis_manifest.json"
    try:
        if p.exists():
            return load_json(p)
    except Exception:
        pass
    return {}


_PAINEIS = _load_paineis()


def _load_efeitos():
    """Mapa sid -> efeito da BIBLIOTECA_EFEITOS (escolhido pela narracao)."""
    proj = os.environ.get("VIDEOMAKER_PROJ", "")
    p = Path(proj) / "artifacts" / "efeitos_por_cena.json"
    try:
        if p.exists():
            return load_json(p)
    except Exception:
        pass
    return {}


_EFEITOS = _load_efeitos()


def _particulas_html(sid, start, dur):
    """Gera HTML+JS de particulas tematicas para uma cena."""
    cfg = _EFEITOS.get(sid)
    if not cfg:
        return "", ""
    import random as _rnd
    rnd = _rnd.Random(abs(hash(sid)) % 100000)
    efeito = cfg.get("efeito", "")
    # quantidade e classe por efeito (TRIPLICADO a pedido do usuario:
    # efeitos apareciam mas com elementos demais escondidos / pouco visiveis)
    QTD = {"bolinhas_sabao":75, "folhinhas_vento":120, "estrelinhas":90,
           "abelhinhas":36, "coracoes":60, "ossinhos":45,
           "racao_varios_formatos":105, "soninho_zzz":24, "chuva":180,
           "fumacinha":60, "passarinhos":54}
    CLS = {"bolinhas_sabao":"part-bolha", "folhinhas_vento":"part-folha",
           "estrelinhas":"part-estrela", "abelhinhas":"part-abelha",
           "coracoes":"part-coracao", "ossinhos":"part-osso",
           "racao_varios_formatos":"part-racao", "soninho_zzz":"part-zzz",
           "chuva":"part-gota", "fumacinha":"part-fumaca",
           "passarinhos":"part-passaro"}
    qtd = QTD.get(efeito, 20)
    cls = CLS.get(efeito, "part-bolha")
    html, js = [], []
    for i in range(qtd):
        x = rnd.randint(0, 1850)
        y0 = rnd.randint(0, 1000)
        size = rnd.choice([14,18,24,30,38]) if efeito not in ("fumacinha","soninho_zzz") else rnd.choice([160,210,270])
        dur_i = rnd.uniform(max(2, dur*0.25), max(3, dur*0.7))
        delay = rnd.uniform(0, max(0.1, dur*0.5))
        opac = rnd.uniform(0.55, 0.9)  # mais visiveis
        pid = f"{sid}-p{i}"
        html.append(f'<div class="particula {cls}" id="{pid}" style="left:{x}px;top:{y0}px;'
                    f'width:{size}px;height:{size}px;background-size:contain;background-repeat:no-repeat"></div>')
        # movimento: sobe (ou desce para chuva/folhas) com leve deriva lateral
        if efeito in ("chuva","folhinhas_vento","passarinhos","abelhinhas"):
            dy = 1200  # desce/atravessa
            dx = rnd.randint(-300, 300)
        else:
            dy = -900  # sobe
            dx = rnd.randint(-200, 200)
        js.append(
            f'tl.fromTo("#{pid}",{{y:0,x:0,opacity:0}},'
            f'{{y:{dy},x:{dx},opacity:{opac:.2f},duration:{dur_i:.2f},ease:"none"}},'
            f'{start+delay:.3f});'
        )
        # fade out no fim
        js.append(f'tl.to("#{pid}",{{opacity:0,duration:0.5}},{start+dur-0.6:.3f});')
    return "".join(html), "\n".join(js)

# Textos da capa e do encerramento, no idioma do video (regra: nenhum texto
# na tela pode ficar em PT nos videos EN/ES). Padrao pt = comportamento antigo.
INTRO_TEXTS = {
    "pt": "Uma nova aventura com a Frida e a Luna!",
    "en": "A brand-new adventure with Frida and Luna!",
    "es": "Una nueva aventura con Frida y Luna!",
}
# Nome do canal na capa. Em EN/ES nao pode sair "FRIDA E LUNA" (PT).
CHANNEL_EYEBROW = {
    "pt": "FRIDA E LUNA",
    "en": "FRIDA AND LUNA",
    "es": "FRIDA Y LUNA",
}
OUTRO_TEXTS = {
    "pt": ["Obrigado por assistir!", "Gostou? Deixe seu like!",
           "Se inscreva no canal", "Novo video toda semana"],
    "en": ["Thanks for watching!", "Liked it? Leave a like!",
           "Subscribe to the channel", "New video every week"],
    "es": ["Gracias por ver!", "Te gusto? Deja tu like!",
           "Suscribete al canal", "Nuevo video cada semana"],
}


def _txt(d, lang):
    return d.get((lang or "pt").lower(), d["pt"])


def build(scene_cfg, timeline, overlays, title="Meu Video", lang="pt"):
    scenes = []
    js = []
    js.append("const tl = gsap.timeline({ paused: true });")

    # ========== TELA INICIAL (CAPA) ==========
    intro_id = "intro-capa"
    intro_start = 0.0
    intro_video = _CLIPS.get("intro", "")
    _proj_intro = Path(os.environ.get("VIDEOMAKER_PROJ", "")) / "assets/images/gemini/scenes"
    _config_intro = intro_video  # veio do video_clips.json

    # REGRA DE OURO (contrato): o intro de boas-vindas TEM que ser falado no
    # idioma da versao. O intro configurado (intro-nova-8s.mp4) tem voz PT;
    # para ES/EN existem as versoes dubladas intro-nova-8s_<lang>.mp4.
    # Sempre prioriza a versao com sufixo do idioma quando ela existir.
    _lang = (lang or "pt").lower()
    if _config_intro and _config_intro.lower().endswith(".mp4"):
        _base, _ext = _config_intro.rsplit(".", 1)
        _localizado = f"{_base}_{_lang}.{_ext}"
        if (_proj_intro / _localizado).exists():
            intro_video = _localizado
            print("  intro no idioma %s -> %s" % (_lang.upper(), _localizado), flush=True)
    # Fallback: se o intro escolhido nao existir no projeto, usa os intros
    # por idioma dos projetos antigos (intro_8s_pt/_es.mp4, original para en).
    if not (intro_video and (_proj_intro / intro_video).exists()):
        _intro_por_idioma = {
            "pt": "intro_8s_pt.mp4",
            "es": "intro_8s_es.mp4",
            "en": "intro_8s.mp4",
        }
        _cand = _intro_por_idioma.get(_lang, "")
        if _cand and (_proj_intro / _cand).exists():
            intro_video = _cand
            print("  intro fallback idioma %s -> %s" % (_lang.upper(), _cand), flush=True)
    # Avisa o preprocess_images qual intro copiar para o workspace
    # (ele roda depois e precisa do MESMO nome escolhido aqui).
    try:
        _marker = (Path(os.environ.get("VIDEOMAKER_PROJ", "")) /
                   "artifacts" / "_intro_usado.txt")
        _marker.parent.mkdir(parents=True, exist_ok=True)
        _marker.write_text(intro_video or "", encoding="utf-8")
    except Exception:
        pass
    if intro_video:
        cam_intro = ('<video class="cam cam-0 intro-video" src="assets/images/%s" '
                     'muted playsinline autoplay loop></video>' % intro_video)
    else:
        cam_intro = ('<img class="cam cam-0" '
                     'src="assets/images/apresenta_o_do_canal_scene.jpg" alt="">')
    # O <video> nao pode ficar dentro de um div com data-start (o HyperFrames
    # exige midia temporizada como filha direta do stage). Por isso o clipe e
    # emitido como elemento de timeline separado, e o div da capa so tem texto.
    intro_html = (
        '<div id="%s" class="clip scene" data-start="%.3f" data-duration="%.3f" data-track-index="1">'
        '<div class="ov grain"></div>'
        '<div class="ov" style="background:radial-gradient(circle at 50%% 50%%,rgba(240,178,74,.18) 0%%,rgba(8,5,3,.95) 100%%)"></div>'
        '<div class="block tc" style="top:42%%;">'
        '<div class="eyebrow">%s</div>'
        '<h1 class="h-xl serif" data-anim="zoom" data-delay="0.3" id="intro-title">%s</h1>'
        '<div class="divider" style="margin:24px auto;"></div>'
        '<div class="body" data-anim="rise" data-delay="0.8">%s</div>'
        '</div>'
        '</div>' % (intro_id, intro_start, INTRO_DUR,
                     _txt(CHANNEL_EYEBROW, lang), title,
                     _txt(INTRO_TEXTS, lang))
    )
    scenes.append(intro_html)
    if intro_video:
        # O intro tem VOZ PROPRIA dublada (PT/EN/ES): nao pode ficar muted.
        # data-has-audio=true faz o HyperFrames renderizar o audio do clipe.
        scenes.append(
            '<video class="cam clip-video" id="intro-video" '
            'src="assets/images/%s" playsinline data-has-audio="true" '
            'data-start="%.3f" data-duration="%.3f" data-track-index="9"></video>'
            % (intro_video, intro_start, INTRO_DUR)
        )
    # ESTRUTURA FINAL:
    #   0-8s   : intro_8s dublado (voz propria) + musica, SEM narracao do pipe
    #   8s+    : cenas deslocadas em +INTRO_DUR, narracao alinhada começa em 8s
    if not intro_video:
        js.append('tl.from("#intro-title",{opacity:0,scale:0.6,duration:0.9,ease:"back.out(2.4)"},0.3);')
        js.append('tl.to("#intro-title",{opacity:0,scale:1.1,duration:0.8,ease:"power2.in"},%.3f);' % (INTRO_DUR - 0.9))
        js.append('tl.fromTo("#intro-capa .cam-0",{scale:1},{scale:1.12,duration:4,ease:"none"},0);')
    cursor = INTRO_DUR  # cenas começam depois do intro

    timeline_shifted = []
    for sec in timeline:
        s = dict(sec)
        s["start"] = round(cursor + sec["start"], 3)
        s["end"] = round(cursor + sec["end"], 3)
        timeline_shifted.append(s)
    cursor = cursor + float(timeline[-1]["end"]) if timeline else cursor

    # Clipes do meio: 'meio' (legado) + 'meio2', 'meio3'... cada um com sua cena
    meio_cfg = _CLIPS.get("meio", {})
    meio_scene = meio_cfg.get("scene", "")
    meio_file = meio_cfg.get("file", "")
    todos_meios = [cfg for key, cfg in _CLIPS.items()
                   if (key == "meio" or key.startswith("meio")) and isinstance(cfg, dict) and cfg.get("file")]
    if not todos_meios and meio_file:
        todos_meios = [meio_cfg]

    for idx, sec in enumerate(timeline_shifted):
        sid = sec["id"]
        start = float(sec["start"])
        dur = float(sec["duration"])
        cfg = scene_cfg.get(sid, {})
        images = cfg.get("images", [])
        cams = cfg.get("camera", [])
        split = cfg.get("split")
        at = cfg.get("at")
        # Clipes de video desta cena (pode haver varios na MESMA cena).
        # O PRIMEIro continua sendo o 'principal' (controla o deslocamento das
        # imagens), os demais sao apenas adicionados no tempo via 'offset'.
        clipes_da_cena = [m for m in todos_meios if m.get("scene") == sid]
        clipe_da_cena = clipes_da_cena[0] if clipes_da_cena else None
        meio_clip_dur = float(clipe_da_cena.get("clip_dur", 8.0)) if clipe_da_cena else 8.0
        meio_file = clipe_da_cena.get("file", "") if clipe_da_cena else ""
        meio_mode = clipe_da_cena.get("mode", "hybrid") if clipe_da_cena else "hybrid"
        meio_offset = float(clipe_da_cena.get("offset", 0.0)) if clipe_da_cena else 0.0
        if clipe_da_cena:
            print("  clipe do meio na cena %s -> %s (%ss, mode=%s, offset=%ss) + stills" %
                  (sid, meio_file, meio_clip_dur, meio_mode, meio_offset), flush=True)
            for extra in clipes_da_cena[1:]:
                print("  clipe extra na cena %s -> %s (%ss, offset=%ss)" %
                      (sid, extra.get("file"), extra.get("clip_dur", 8.0),
                       extra.get("offset", 0.0)), flush=True)

        trans = str(cfg.get("transicao") or "crossfade").lower()
        T = float(TRANSICOES.get(trans, XFADE)) if trans in TRANSICOES else XFADE
        dur_ext = dur + T
        track = "1" if idx % 2 == 0 else "2"
        parts = ['<div id="%s" class="clip scene" data-start="%.3f" data-duration="%.3f" data-track-index="%s">'
                 % (sid, start, dur_ext, track)]
        # REGRA: nunca deixar buraco no video. Se uma imagem faltou na geracao,
        # reaproveita a ultima imagem valida (desta secao ou da secao anterior).
        # A pasta de imagens e resolvida de IMAGES_DIR (definida pelo chamador) ou
        # do projeto atual via variavel de ambiente VIDEOMAKER_PROJ.
        _proj = os.environ.get("VIDEOMAKER_PROJ")
        # As imagens de cena ficam em assets/images/gemini/scenes (ver
        # preprocess_images.py). Checar em assets/images fazia TODA imagem
        # parecer faltante e ser trocada pela anterior (bug: mesma imagem
        # repetida por um minuto).
        dir_images = ((Path(_proj) / "assets" / "images" / "gemini" / "scenes")
                      if _proj else None)
        ultima_valida = None
        images_resolvidas = []
        for name in images:
            if name.lower().endswith(".mp4"):
                images_resolvidas.append(name)
                continue
            caminho = (dir_images / name) if dir_images else None
            if caminho is not None and not caminho.exists():
                if ultima_valida is not None:
                    print("  AVISO: imagem faltando '%s' -> reaproveitando '%s'" % (name, ultima_valida), flush=True)
                    images_resolvidas.append(ultima_valida)
                    continue
            images_resolvidas.append(name)
            ultima_valida = name

        videos_desta_cena = []
        # Emite TODOS os clipes desta cena. Modo "middle": clipe entra em
        # start+offset. Modo "hybrid" (padrao): clipe no inicio da cena.
        # Clipes extras (ex.: meio3) usam SEMPRE o seu proprio 'offset'.
        for ci, clp in enumerate(clipes_da_cena):
            cfile = clp.get("file", "")
            if not cfile:
                continue
            cdur = float(clp.get("clip_dur", 8.0))
            cmode = clp.get("mode", "hybrid")
            coff = float(clp.get("offset", 0.0))
            if cmode == "middle" or ci > 0:
                clip_start = start + coff
            else:
                clip_start = start
            vid_id = "%s-video" % sid if ci == 0 else "%s-video-%d" % (sid, ci)
            videos_desta_cena.append(
                '<video class="cam clip-video" id="%s" '
                'src="assets/images/%s" muted playsinline '
                'data-start="%.3f" data-duration="%.3f" data-track-index="%s"></video>'
                % (vid_id, cfile, clip_start, cdur, track)
            )
        for i, name in enumerate(images_resolvidas):
            cls = "cam cam-%d%s" % (i, " cam-b" if i > 0 else "")
            if name.lower().endswith(".mp4"):
                # Midia temporizada deve ser filha direta do stage (check do
                # HyperFrames), nao ficar dentro do div data-start da cena.
                videos_desta_cena.append(
                    '<video class="%s clip-video" id="%s-video" '
                    'src="assets/images/%s" muted playsinline '
                    'data-start="%.3f" data-duration="%.3f" data-track-index="%s"></video>'
                    % (cls, sid, name, start, dur, track)
                )
            else:
                parts.append('<img class="%s" src="assets/images/%s" alt="">' % (cls, name))

        overlay = overlays.get(sid, "")
        parts.append(overlay)
        parts.append('<div class="ov grain"></div>')
        # particulas tematicas da BIBLIOTECA_EFEITOS (movimento sem zoom)
        p_html, p_js = _particulas_html(sid, start, dur)
        parts.append(p_html)
        parts.append("</div>")
        scenes.append("".join(parts))
        scenes.extend(videos_desta_cena)
        if p_js:
            js.append(p_js)

        n_img = len(images)
        has_video = any(n.lower().endswith(".mp4") for n in images)

        imagens_apos_clipe = bool(meio_file)  # clipe_da_cena ja e especifico da cena
        meio_middle = imagens_apos_clipe and meio_mode == "middle"
        inicio_imgs = start + (0.0 if meio_middle else
                               (meio_clip_dur if imagens_apos_clipe else 0.0))
        dur_imgs = dur
        # no modo 'hybrid' as imagens entram depois do clipe
        if imagens_apos_clipe and not meio_middle:
            inicio_imgs = start + meio_clip_dur
            dur_imgs = dur - meio_clip_dur

        def _reveal_time(i):
            # Tempo absoluto em que a imagem i entra. 'at' e fracao 0..1 da cena.
            if at is not None and i < len(at):
                frac = float(at[i])
            elif split is not None and n_img == 2 and i == 1:
                frac = float(split)
            elif n_img > 1:
                frac = i / float(n_img)
            else:
                frac = 0.0
            if meio_middle:
                # imagens antes do clipe: tempo normal; depois: empurradas pelo clipe
                t = start + frac * dur
                clip_at = start + meio_offset
                if t >= clip_at:
                    t += meio_clip_dur
                return min(t, start + dur)
            return inicio_imgs + frac * dur_imgs

        for i, name in enumerate(images):
            if name.lower().endswith(".mp4"):
                continue
            cam = cams[i] if i < len(cams) else [1.02, 1.10, 0, 14, 0, -8]
            s0, s1, x0, x1, y0, y1 = cam
            # REGRA do usuario: colagem (2/3/4 paineis) ja tem muita informacao:
            # NAO fazer zoom vai-e-vem (isso corta os paineis). So uma leve
            # deriva lenta. Zoom dinamico apenas em imagem unica.
            n_pain = _PAINEIS.get(name, 1)
            if n_pain > 1:
                # REGRA DURA: colagens (2/3/4 paineis) ja preenchem toda a tela.
                # ZERO movimento (nem Ken Burns, nem deriva): qualquer escala
                # corta os paineis. Mantem fixo em scale:1, x:0, y:0.
                js.append(
                    'tl.set("#%s .cam-%d",{scale:1,x:0,y:0},%.3f);'
                    % (sid, i, _reveal_time(i))
                )
                continue
            # Variação de zoom por beat para evitar repetição: algumas cenas começam
            # com zoom máximo e diminuem, outras começam mínimo e aumentam.
            scale_pairs = [(1.50,1.05),(1.05,1.50),(1.38,1.10),(1.10,1.45)]
            idx = 0
            # usa seed da cena + indice para variação determinística
            try:
                idx = (abs(hash(sid)) + i) % len(scale_pairs)
                s0_raw, s1_raw = scale_pairs[idx]
                # só substitui se o camera original for o padrão
                if abs(float(s0)-1.02) < 0.01 and abs(float(s1)-1.10) < 0.01:
                    s0, s1 = s0_raw, s1_raw
            except Exception:
                pass
            # Vibrancia: amplia o movimento (scale + deslocamento) para o
            # movimento nao parecer lento.
            s0f = 1.0 + (float(s0) - 1.0) * CAM_VIBRANCI
            s1f = 1.0 + (float(s1) - 1.0) * CAM_VIBRANCI
            x0f = float(x0) * CAM_VIBRANCI
            x1f = float(x1) * CAM_VIBRANCI
            y0f = float(y0) * CAM_VIBRANCI
            y1f = float(y1) * CAM_VIBRANCI
            # Camera por BEAT: cada imagem se move durante o seu proprio
            # segmento (ate a proxima imagem), com ease in/out + overshoot.
            # Antes era um movimento unico linear de 10-16 s (parecia lento).
            t_i = _reveal_time(i)
            t_next = (_reveal_time(i + 1) if i + 1 < n_img
                      else (start + dur))
            seg = max(0.8, t_next - t_i)
            # Variação de animação: alguns beats crescem só, outros fazem yoyo
            if idx % 3 == 0:
                # crescendo contínuo até o fim do beat (zoom vai ficando grandão)
                js.append(
                    'tl.fromTo("#%s .cam-%d",{scale:%s,x:%s,y:%s},'
                    '{scale:%s,x:%s,y:%s,duration:%.3f,ease:%s},%.3f);'
                    % (sid, i, s0f, x0f, y0f,
                       s1f, x1f, y1f, seg, EASE_CAMERA, t_i)
                )
            else:
                js.append(
                    'tl.fromTo("#%s .cam-%d",{scale:%s,x:%s,y:%s},'
                    '{scale:%s,x:%s,y:%s,duration:%.3f,ease:%s,repeat:1,yoyo:true},%.3f);'
                    % (sid, i, s0f, x0f, y0f,
                       s1f, x1f, y1f, seg/2, EASE_CAMERA, t_i)
                )

        if n_img <= 1 or has_video:
            # Cena com imagem unica (ou so video): fade de entrada/saida pela
            # duracao da transicao escolhida.
            js.append('tl.set("#%s",{opacity:0},0);' % sid)
            if T > 0:
                js.append('tl.to("#%s",{opacity:1,duration:%.2f,ease:"power1.out"},%.3f);'
                          % (sid, T, start))
                js.append('tl.to("#%s",{opacity:0,duration:%.2f,ease:%s},%.3f);'
                          % (sid, T, EASE_SAIDA, start + dur - 0.05))
        else:
            # Multi-imagem: crossfade no tempo da pausa (beat) da narracao.
            # Cada imagem entra no beat correspondente e a anterior sai por
            # cima do crossfade (sem dead frame: fade-out e fade-in se sobrepoem).
            js.append('tl.set("#%s .cam-0",{opacity:0},0);' % sid)
            js.append('tl.to("#%s .cam-0",{opacity:1,duration:%.2f,ease:%s},%.3f);'
                      % (sid, T, EASE_IMAGEM, start))
            for i in range(1, n_img):
                t_i = _reveal_time(i)
                js.append('tl.to("#%s .cam-%d",{opacity:1,duration:%.2f,ease:%s},%.3f);'
                          % (sid, i, T, EASE_IMAGEM, t_i))
                js.append('tl.to("#%s .cam-%d",{opacity:0,duration:%.2f,ease:%s},%.3f);'
                          % (sid, i - 1, T, EASE_SAIDA, t_i))
            js.append('tl.to("#%s .cam-%d",{opacity:0,duration:%.2f,ease:%s},%.3f);'
                      % (sid, n_img - 1, T, EASE_SAIDA, start + dur - 0.05))

        for a in collect_anims(overlay, sid):
            aid = a["id"]
            kind = a.get("data-anim", "rise")
            if "data-at" in a:
                t = start + float(a["data-at"]) * dur
            else:
                t = start + float(a.get("data-delay", 0))
            props = ANIM.get(kind, ANIM["rise"])
            pd = ", ".join("%s:%s" % (k, json.dumps(v)) for k, v in props.items())
            d = DUR_ANIM.get(kind, DUR_ANIM_PADRAO)
            ease = EASE.get(kind, '"power3.out"')
            js.append('tl.from("#%s",{%s,duration:%s,ease:%s},%.3f);' % (aid, pd, d, ease, t))
            if "data-float" in a:
                remaining = max(0.0, (start + dur) - (t + d))
                reps = max(1, int(remaining / 1.7))
                try:
                    pct = float(a["data-float"]) if a["data-float"] else 3.0
                except ValueError:
                    pct = 3.0
                js.append('tl.fromTo("#%s",{yPercent:0},{yPercent:%s,duration:1.7,yoyo:true,repeat:%d,ease:"sine.inOut"},%.3f);'
                          % (aid, json.dumps(pct), reps, t + d))
            if "data-out" in a:
                to = start + float(a["data-out"]) * dur
                js.append('tl.to("#%s",{opacity:0,y:-22,duration:0.55,ease:"power2.in"},%.3f);'
                          % (aid, to))

    # (sem soma extra: as cenas ja foram deslocadas em +INTRO_DUR no inicio,
    #  entao o cursor ja inclui os 8s do intro. Isso evita o buraco de tela
    #  escura que havia entre o fim da narracao e o pre-final.)

    # ========== CLIPES FINAIS SINCRONIZADOS COM A FALA ==========
    # Os clipes nao vao DEPOIS da cena s_outro: sobrepoem a cena no instante
    # exato em que a narração fala cada coisa:
    #   "obrigado por assistir" -> pre_final (pata com confete)
    #   "deixe seu like, se inscreva" -> subscribe (logo YouTube + joinha)
    pre_final = _CLIPS.get("pre_final", {})
    pre_file = pre_final.get("file", "") if isinstance(pre_final, dict) else ""
    pre_dur = float(pre_final.get("dur", 8.0)) if isinstance(pre_final, dict) else 8.0
    outro_video = _CLIPS.get("outro", "")
    outro_dur = float(_CLIPS.get("outro_dur", 8.0))

    # Encontra a cena s_outro e os tempos de seus beats no timeline ja deslocado
    outro_scene_start = None
    outro_scene_dur = 0.0
    outro_beats_at = []
    for sec in timeline_shifted:
        if sec["id"] == "s_outro":
            outro_scene_start = float(sec["start"])
            outro_scene_dur = float(sec["duration"])
            break
    cfg_outro = scene_cfg.get("s_outro", {})
    outro_beats_at = cfg_outro.get("at", []) if isinstance(cfg_outro, dict) else []

    if pre_file and outro_scene_start is not None:
        # pre_final entra no comeco da fala de agradecimento
        pre_start = outro_scene_start
        scenes.append(
            '<video class="cam clip-video" id="pre-final-video" '
            'src="assets/images/%s" muted playsinline '
            'data-start="%.3f" data-duration="%.3f" data-track-index="3"></video>'
            % (pre_file, pre_start, pre_dur)
        )
        # subscribe entra quando fala "like/se inscreva" (beat 1 de s_outro)
        sub_start = outro_scene_start + (outro_beats_at[1] * outro_scene_dur
                                         if len(outro_beats_at) > 1 else 0.5 * outro_scene_dur)
        scenes.append(
            '<video class="cam clip-video" id="outro-video" '
            'src="assets/images/%s" muted playsinline '
            'data-start="%.3f" data-duration="%.3f" data-track-index="4"></video>'
            % (outro_video, sub_start, outro_dur)
        )
        # o cursor nao avanca: os clipes sobrepoem a cena, nao a estendem

    # ========== TELA FINAL (OUTRO) ==========
    outro_id = "outro-final"
    outro_start = cursor
    outro_txts = _txt(OUTRO_TEXTS, lang)
    outro_video = _CLIPS.get("outro", "")
    if outro_video:
        # Video ja traz logo do YouTube + joinha + SUBSCRIBE embutidos.
        # Nao sobrepoem os textos para nao competir com o SUBSCRIBE do clipe.
        cam_outro = ('<video class="cam cam-0 outro-video" src="assets/images/%s" '
                     'muted playsinline autoplay loop></video>' % outro_video)
        cta_bloco = ('<div class="block tc" style="top:88%%;">'
                     '<div class="body" data-anim="rise" data-delay="0.4">%s</div>'
                     '</div>' % outro_txts[0])
    else:
        cam_outro = ('<div class="ov" style="background:radial-gradient(circle at 50%% 50%%,'
                     'rgba(240,178,74,.18) 0%%,rgba(8,5,3,.95) 100%%)"></div>')
        cta_bloco = (
            '<div class="block tc" style="top:38%%;">'
            '<div class="h-lg serif" data-anim="pop" data-delay="0.2">%s</div>'
            '<div class="divider" style="margin:24px auto;"></div>'
            '<div class="body" data-anim="rise" data-delay="0.6">%s</div>'
            '<div class="body" data-anim="rise" data-delay="1.1">%s</div>'
            '<div class="body" data-anim="rise" data-delay="1.6">%s</div>'
            '</div>' % (outro_txts[0], outro_txts[1], outro_txts[2], outro_txts[3])
        )
    outro_html = (
        '<div id="%s" class="clip scene" data-start="%.3f" data-duration="%.3f" data-track-index="%s">'
        '<div class="ov grain"></div>'
        '%s'
        '</div>' % (outro_id, outro_start, OUTRO_DUR, "1", cta_bloco)
    )
    scenes.append(outro_html)
    # O subscribe (outro-video) ja foi posicionado dinamicamente dentro da
    # cena s_outro, sincronizado com a fala "like/se inscreva". NAO adicionar
    # outro aqui (evita duplicata). A tela final abaixo serve como "fotos de
    # despedida" caso sobre narração depois dos 8s do clipe.
    js.append('tl.set("#%s",{opacity:0},0);' % outro_id)
    if not outro_video:
        js.append('tl.from("#%s .h-lg",{opacity:0,scale:0.5,duration:0.8,ease:"back.out(2.4)"},%.3f);' % (outro_id, outro_start + 0.2))
        for delay, sel in [(0.6, ".body:nth-of-type(1)"), (1.1, ".body:nth-of-type(2)"), (1.6, ".body:nth-of-type(3)")]:
            js.append('tl.from("#%s %s",{opacity:0,y:30,duration:0.55,ease:"power3.out"},%.3f);' % (outro_id, sel, outro_start + delay))
    else:
        js.append('tl.from("#%s .body",{opacity:0,y:30,duration:0.6,ease:"power3.out"},%.3f);' % (outro_id, outro_start + 0.4))
    js.append('tl.to("#%s",{opacity:0,duration:0.8,ease:"power2.in"},%.3f);' % (outro_id, outro_start + OUTRO_DUR - 0.9))

    # A tela de fotos de despedida cobre ate o fim do mix (musica termina no
    # ultimo segundo). O mix tem INTRO+timeline+pre+outro = 705s; como os
    # clipes finais agora sobrepoem a cena, estendemos a tela final ate la.
    mix_path = (Path(os.environ.get("VIDEOMAKER_PROJ", "")) / "assets" / "audio" / "final_mix.m4a")
    mix_dur = 0.0
    if mix_path.exists():
        try:
            import subprocess as _sp
            _cfg = load_json(HERE / "config.json")
            _ffprobe = Path(_cfg["ffmpeg_dir"]) / "ffprobe.exe"
            _r = _sp.run([str(_ffprobe), "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(mix_path)],
                         capture_output=True, text=True)
            mix_dur = float(_r.stdout.strip())
        except Exception:
            pass
    outro_dur_real = max(OUTRO_DUR, mix_dur - outro_start)
    # ajusta a duracao da ultima cena no HTML e na animacao de fade
    if abs(outro_dur_real - OUTRO_DUR) > 0.01:
        scenes[-1] = scenes[-1].replace(
            'data-duration="%.3f"' % OUTRO_DUR,
            'data-duration="%.3f"' % outro_dur_real, 1)
        js_txt = "\n".join(js).replace(
            "outro_start + OUTRO_DUR - 0.9", "outro_start + %.3f - 0.9" % outro_dur_real)
        js = js_txt.split("\n")

    total = outro_start + outro_dur_real
    js.append('window.__timelines["main"] = tl;')

    return "\n".join(scenes), "\n".join(js), total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=str(PROJECT / "artifacts" / "timeline.json"))
    ap.add_argument("--out", default=str(PROJECT / "hyperframes-workspace" / "index.html"))
    ap.add_argument("--scenes", default=str(HERE / "scenes.json"))
    ap.add_argument("--scenes-dir", default=str(HERE / "scenes"))
    ap.add_argument("--proj", default=None, help="diretorio do projeto (para ler script.json)")
    ap.add_argument("--lang", default="pt", help="idioma do video (pt,en,es) — usado para ler o titulo traduzido em script_<lang>.json")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    scene_cfg = load_json(args.scenes)
    scenes_dir = Path(args.scenes_dir)
    tl = load_json(args.timeline)["timeline"]

    # pega o titulo do script do projeto, no idioma do video (script_<lang>.json
    # quando existe, cai de volta para script.json). Assim a capa/overlay de
    # abertura fica escrita na mesma lingua da narracao do video final.
    proj_dir = Path(args.proj).resolve() if args.proj else Path(args.out).resolve().parent.parent
    lang = (args.lang or "pt").strip().lower()
    script_candidates = [proj_dir / "artifacts" / ("script_%s.json" % lang), proj_dir / "artifacts" / "script.json"]

    video_title = "Meu Video"
    for script_path in script_candidates:
        try:
            script = load_json(script_path)
            video_title = script.get("title", video_title)
            break
        except Exception:
            continue

    overlays = {}
    for sec in tl:
        p = scenes_dir / ("%s.html" % sec["id"])
        if p.exists():
            html = p.read_text(encoding="utf-8")
            overlays[sec["id"]] = inject_ids(html, sec["id"])

    body, js, total = build(scene_cfg, tl, overlays, title=video_title, lang=lang)
    # Narração começa em INTRO_DUR (logo após o intro dublado) e vai até o
    # último frame. Os 8s iniciais ficam só com a voz do intro + música.
    audio_start = INTRO_DUR
    audio_dur = total - INTRO_DUR

    html = """<!doctype html>
<html lang="pt-BR" data-lang="%s" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>%s</style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="%.3f"
         data-width="1920" data-height="1080">
%s
      <audio id="intro-music" src="intro_music.m4a" data-start="0.000" data-duration="%.3f"
             data-track-index="1" data-volume="1"></audio>
      <audio id="mix-audio" src="final_mix.m4a" data-start="%.3f" data-duration="%.3f"
             data-track-index="2" data-volume="1"></audio>
    </div>
    <script>
%s
    </script>
  </body>
</html>
""" % (lang, CSS, total, body, INTRO_DUR, audio_start, audio_dur, js)

    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    # Carimbo do idioma desta composicao. O render.ps1 valida contra o slug
    # (video _es precisa de composicao es) e ABORTA se nao bater - foi assim
    # que o video PT acabou renderizado com a composicao/mix de outro idioma
    # (bug 2026-11-16).
    out.with_suffix(out.suffix + ".lang").write_text(lang + "\n", encoding="utf-8")
    print("wrote", out, len(html), "bytes; total", total, "s; idioma", lang)


if __name__ == "__main__":
    main()
