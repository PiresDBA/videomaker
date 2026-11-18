# -*- coding: utf-8 -*-
"""gerar_sonoplastia.py - Gera efeitos PROCEDURAIS e os mixa por cima do
final_mix.m4a atual (que ja tem narracao + musica + ducking).

Nao altera o mix original — gera final_mix_sonoplastia.m4a.

Efeitos sao sintetizados com ffmpeg (sine/noise + filtros + envelope), sem
depender de biblioteca de sons externa. Le o mapa de sonoplastia gerado por
sugerir_sonoplastia.py e converte cada sugestao em um curto WAV colado no
tempo certo com adelay.
"""
from __future__ import annotations
import re, sys, subprocess, tempfile, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FF = shutil.which("ffmpeg") or r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
AUD = P / "assets/audio"
MAPA = P / "artifacts/auditoria/mapa_sonoplastia.txt"
MIX_ORIG = AUD / "final_mix.m4a"
MIX_NOVO = AUD / "final_mix_sonoplastia.m4a"
SR = 44100

# tipos de efeito -> (gerador ffmpeg, duracao s, ganho)
# cada gerador produz 1s de audio mono no tempo 0; o adelay posiciona
TIPOS = {
    "CLIPE":    ("swish",   0.7, 0.28),
    "ABERTURA": ("chord",   1.2, 0.30),
    "FOLEY":    ("foley",   0.45, 0.16),
    "TRANSICAO":("whoosh",  0.45, 0.13),
    "CTA":      ("bell",    0.9, 0.32),
}
# ajuste de ganho por palavra-chave no motivo
GANHO_PALAVRA = {
    "espirro": 0.34, "osso": 0.30, "bola": 0.30, "mágic": 0.26,
    "poeira": 0.26, "confete": 0.34, "subscribe": 0.36, "fanfarra": 0.32,
}


def parse_mapa():
    itens = []
    for line in MAPA.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\d+):([\d.]+)\s+(\w+)\s+(\w+)\s+(.*)", line)
        if not m:
            continue
        t = int(m.group(1)) * 60 + float(m.group(2))
        tipo = m.group(3)
        motivo = m.group(5)
        if tipo not in TIPOS:
            continue
        itens.append({"t": t, "tipo": tipo, "motivo": motivo})
    return itens


def filtro_efeito(kind):
    """Retorna (filtro ffmpeg de entrada, duracao). Gera audio de 1s."""
    if kind == "swish":   # subida rapida + brilho
        return ("sine=frequency=880:sample_rate=%d,"
                "tremolo=f=12:d=0.8,"
                "afade=t=in:st=0:d=0.05,afade=t=out:st=0.2:d=0.5" % SR, 0.7)
    if kind == "chord":   # acorde alegre (3 senos somados)
        return ("sine=frequency=523.25:sample_rate=%d,"
                "afade=t=in:st=0:d=0.05,afade=t=out:st=0.5:d=0.7" % SR, 1.2)
    if kind == "whoosh":  # ruido filtrado passante (simula whoosh)
        return ("anoisesrc=color=pink:amplitude=0.6:sample_rate=%d,"
                "highpass=f=400,lowpass=f=3000,"
                "afade=t=in:st=0:d=0.08,afade=t=out:st=0.15:d=0.3" % SR, 0.45)
    if kind == "bell":    # campainha (sino = seno com decaimento)
        return ("sine=frequency=1318.5:sample_rate=%d,"
                "tremolo=f=8:d=0.5,"
                "afade=t=in:st=0:d=0.01,afade=t=out:st=0.1:d=0.8" % SR, 0.9)
    # foley generico: ruido curto com envelope (serve para passos, tigela, asas...)
    return ("anoisesrc=color=white:amplitude=0.4:sample_rate=%d,"
            "bandpass=f=1200:width_type=o:w=2,"
            "afade=t=in:st=0:d=0.01,afade=t=out:st=0.08:d=0.35" % SR, 0.45)


def ganho(item):
    g = TIPOS[item["tipo"]][2]
    for k, v in GANHO_PALAVRA.items():
        if k in item["motivo"].lower():
            g = max(g, v)
    return g


def main():
    if not MIX_ORIG.exists():
        print("ERRO: mix original nao encontrado:", MIX_ORIG)
        sys.exit(1)
    if not MAPA.exists():
        print("ERRO: mapa de sonoplastia nao encontrado:", MAPA)
        sys.exit(1)

    itens = parse_mapa()
    print(f"Itens de sonoplastia: {len(itens)}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # gera um WAV por efeito e aplica volume + delay num unico filtro
        cmd = [FF, "-y", "-v", "error", "-i", str(MIX_ORIG)]
        filtros = []
        mixes = []
        for i, it in enumerate(itens):
            kind, dur, _ = TIPOS[it["tipo"]]
            todo, _d = filtro_efeito(kind)
            wav = td / f"e{i:03d}.wav"
            subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", todo,
                            "-t", str(_d), "-ac", "1", "-ar", str(SR),
                            "-c:a", "pcm_s16le", str(wav)], check=True)
            cmd += ["-i", str(wav)]
            g = ganho(it)
            delay_ms = int(it["t"] * 1000)
            filtros.append(f"[{i+1}:a]volume={g:.3f},adelay={delay_ms}:all=1[e{i}]")
            mixes.append(f"[e{i}]")

        n = len(itens) + 1
        # mix: original + efeitos (os efeitos entram em baixo volume sob a voz)
        soma = "".join(mixes)
        filtros.append(f"[0:a]{soma}amix=inputs={n}:duration=first:dropout_transition=0:normalize=0[out]")
        cmd += ["-filter_complex", ";".join(filtros), "-map", "[out]",
                "-c:a", "aac", "-b:a", "192k", str(MIX_NOVO)]
        subprocess.run(cmd, check=True)

    print(f"Novo mix gerado: {MIX_NOVO} ({MIX_NOVO.stat().st_size} bytes)")
    print(f"Itens aplicados: {len(itens)}")


if __name__ == "__main__":
    main()
