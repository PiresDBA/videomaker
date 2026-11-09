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
.cam-b{opacity:0}
.ov{position:absolute;inset:0;pointer-events:none}
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
    "zoom":   '"power3.out"',
    "line":   '"power3.out"',
    "soft":   '"power1.out"',
}


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


XFADE = 0.9  # crossfade entre cenas (ajustavel)

INTRO_DUR = 4.0   # duracao da tela inicial (capa)
OUTRO_DUR = 5.0   # duracao da tela final (agradecimento)


def build(scene_cfg, timeline, overlays, title="Meu Video"):
    scenes = []
    js = []
    js.append("const tl = gsap.timeline({ paused: true });")

    # ========== TELA INICIAL (CAPA) ==========
    intro_id = "intro-capa"
    intro_start = 0.0
    scenes.append(
        '<div id="%s" class="clip scene" data-start="%.3f" data-duration="%.3f" data-track-index="1">'
        '<div class="ov grain"></div>'
        '<img class="cam cam-0" src="assets/images/apresenta_o_do_canal_scene.jpg" alt="">'
        '<div class="ov" style="background:radial-gradient(circle at 50%% 50%%,rgba(240,178,74,.18) 0%%,rgba(8,5,3,.95) 100%%)"></div>'
        '<div class="block tc" style="top:42%%;">'
        '<div class="eyebrow">FRIDA E LUNA</div>'
        '<h1 class="h-xl serif" data-anim="zoom" data-delay="0.3" id="intro-title">%s</h1>'
        '<div class="divider" style="margin:24px auto;"></div>'
        '<div class="body" data-anim="rise" data-delay="0.8">Uma nova aventura com a Frida e a Luna!</div>'
        '</div>'
        '</div>' % (intro_id, intro_start, INTRO_DUR, title)
    )
    js.append('tl.from("#intro-title",{opacity:0,scale:0.6,duration:1.2,ease:"back.out(2.4)"},0.3);')
    js.append('tl.to("#intro-title",{opacity:0,scale:1.1,duration:0.8,ease:"power2.in"},%.3f);' % (INTRO_DUR - 0.9))
    js.append('tl.fromTo("#intro-capa .cam-0",{scale:1},{scale:1.12,duration:4,ease:"none"},0);')
    cursor = INTRO_DUR

    # Desloca todas as cenas originais apos a capa
    timeline_shifted = []
    for sec in timeline:
        s = dict(sec)
        s["start"] = round(cursor + sec["start"], 3)
        s["end"] = round(cursor + sec["end"], 3)
        timeline_shifted.append(s)
    cursor = cursor + float(timeline[-1]["end"]) if timeline else cursor

    for idx, sec in enumerate(timeline_shifted):
        sid = sec["id"]
        start = float(sec["start"])
        dur = float(sec["duration"])
        cfg = scene_cfg.get(sid, {})
        images = cfg.get("images", [])
        cams = cfg.get("camera", [])
        split = cfg.get("split")
        at = cfg.get("at")

        dur_ext = dur + XFADE
        track = "1" if idx % 2 == 0 else "2"
        parts = ['<div id="%s" class="clip scene" data-start="%.3f" data-duration="%.3f" data-track-index="%s">'
                 % (sid, start, dur_ext, track)]
        for i, name in enumerate(images):
            cls = "cam cam-%d%s" % (i, " cam-b" if i > 0 else "")
            if name.lower().endswith(".mp4"):
                parts.append('<video class="%s" src="assets/images/%s" muted playsinline></video>' % (cls, name))
            else:
                parts.append('<img class="%s" src="assets/images/%s" alt="">' % (cls, name))

        overlay = overlays.get(sid, "")
        parts.append(overlay)
        parts.append('<div class="ov grain"></div>')
        parts.append("</div>")
        scenes.append("".join(parts))

        for i, name in enumerate(images):
            if name.lower().endswith(".mp4"):
                continue
            cam = cams[i] if i < len(cams) else [1.02, 1.10, 0, 14, 0, -8]
            s0, s1, x0, x1, y0, y1 = cam
            js.append(
                'tl.fromTo("#%s .cam-%d",{scale:%s,x:%s,y:%s},'
                '{scale:%s,x:%s,y:%s,duration:%.3f,ease:"none"},%.3f);'
                % (sid, i, s0, x0, y0, s1, x1, y1, dur_ext + 0.4, start)
            )

        has_video = any(n.lower().endswith(".mp4") for n in images)
        if len(images) > 1 and not has_video:
            # Revela cada imagem extra (cam-1, cam-2, cam-3...) no ponto da
            # PAUSA em que a batida de fala correspondente comeca ("at").
            # Sem "at": 2 imagens usam "split"; 3+ distribui uniformemente.
            n_img = len(images)
            for i in range(1, n_img):
                if at is not None and i < len(at):
                    frac = float(at[i])
                elif split is not None and n_img == 2:
                    frac = float(split)
                else:
                    frac = i / float(n_img)
                js.append('tl.to("#%s .cam-%d",{opacity:1,duration:1.0,ease:"power1.inOut"},%.3f);'
                          % (sid, i, start + frac * dur - 0.5))

        js.append('tl.set("#%s",{opacity:0},0);' % sid)
        js.append('tl.from("#%s",{opacity:0,duration:0.8,ease:"power1.out"},%.3f);'
                  % (sid, start))
        js.append('tl.to("#%s",{opacity:0,duration:%.2f,ease:"power1.in"},%.3f);'
                  % (sid, XFADE, start + dur - 0.05))

        for a in collect_anims(overlay, sid):
            aid = a["id"]
            kind = a.get("data-anim", "rise")
            if "data-at" in a:
                t = start + float(a["data-at"]) * dur
            else:
                t = start + float(a.get("data-delay", 0))
            props = ANIM.get(kind, ANIM["rise"])
            pd = ", ".join("%s:%s" % (k, json.dumps(v)) for k, v in props.items())
            d = 0.55 if kind == "pop" else (0.7 if kind == "line" else (0.9 if kind == "bounce" else 0.8))
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

    # ========== TELA FINAL (OUTRO) ==========
    outro_id = "outro-final"
    outro_start = cursor
    scenes.append(
        '<div id="%s" class="clip scene" data-start="%.3f" data-duration="%.3f" data-track-index="1">'
        '<div class="ov grain"></div>'
        '<div class="ov" style="background:radial-gradient(circle at 50%% 50%%,rgba(240,178,74,.18) 0%%,rgba(8,5,3,.95) 100%%)"></div>'
        '<div class="block tc" style="top:38%%;">'
        '<div class="h-lg serif" data-anim="pop" data-delay="0.2">Obrigado por assistir!</div>'
        '<div class="divider" style="margin:24px auto;"></div>'
        '<div class="body" data-anim="rise" data-delay="0.6">Gostou? Deixe seu like!</div>'
        '<div class="body" data-anim="rise" data-delay="1.1">Se inscreva no canal</div>'
        '<div class="body" data-anim="rise" data-delay="1.6">Novo video toda semana</div>'
        '</div>'
        '</div>' % (outro_id, outro_start, OUTRO_DUR)
    )
    js.append('tl.set("#%s",{opacity:0},0);' % outro_id)
    js.append('tl.from("#%s .h-lg",{opacity:0,scale:0.5,duration:1.0,ease:"back.out(2.4)"},%.3f);' % (outro_id, outro_start + 0.2))
    for delay, sel in [(0.6, ".body:nth-of-type(1)"), (1.1, ".body:nth-of-type(2)"), (1.6, ".body:nth-of-type(3)")]:
        js.append('tl.from("#%s %s",{opacity:0,y:30,duration:0.8,ease:"power3.out"},%.3f);' % (outro_id, sel, outro_start + delay))
    js.append('tl.to("#%s",{opacity:0,duration:0.8,ease:"power2.in"},%.3f);' % (outro_id, outro_start + OUTRO_DUR - 0.9))

    total = outro_start + OUTRO_DUR
    js.append('window.__timelines["main"] = tl;')

    return "\n".join(scenes), "\n".join(js), total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=str(PROJECT / "artifacts" / "timeline.json"))
    ap.add_argument("--out", default=str(PROJECT / "hyperframes-workspace" / "index.html"))
    ap.add_argument("--scenes", default=str(HERE / "scenes.json"))
    ap.add_argument("--scenes-dir", default=str(HERE / "scenes"))
    ap.add_argument("--proj", default=None, help="diretorio do projeto (para ler script.json)")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    scene_cfg = load_json(args.scenes)
    scenes_dir = Path(args.scenes_dir)
    tl = load_json(args.timeline)["timeline"]

    # pega o titulo do script.json do projeto (caminho correto)
    proj_dir = Path(args.proj).resolve() if args.proj else Path(args.out).resolve().parent.parent
    script_path = proj_dir / "artifacts" / "script.json"

    video_title = "Meu Video"
    try:
        script = load_json(script_path)
        video_title = script.get("title", video_title)
    except Exception:
        pass

    overlays = {}
    for sec in tl:
        p = scenes_dir / ("%s.html" % sec["id"])
        if p.exists():
            html = p.read_text(encoding="utf-8")
            overlays[sec["id"]] = inject_ids(html, sec["id"])

    body, js, total = build(scene_cfg, tl, overlays, title=video_title)
    audio_start = 0.0
    audio_dur = total - OUTRO_DUR

    html = """<!doctype html>
<html lang="pt-BR" data-resolution="landscape">
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
      <audio id="mix-audio" src="final_mix.m4a" data-start="%.3f" data-duration="%.3f"
             data-track-index="2" data-volume="1"></audio>
    </div>
    <script>
%s
    </script>
  </body>
</html>
""" % (CSS, total, body, audio_start, audio_dur, js)

    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    print("wrote", out, len(html), "bytes; total", total, "s")


if __name__ == "__main__":
    main()
