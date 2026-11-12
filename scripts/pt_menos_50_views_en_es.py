# -*- coding: utf-8 -*-
"""
Varredura do canal PT: vídeos com < 50 views que são de fato em inglês
ou espanhol, identificados pelo idioma das legendas (captions).

Uso:
  python scripts/pt_menos_50_views_en_es.py --apagar
  python scripts/pt_menos_50_views_en_es.py --dry-run
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from listar_canal import service_for, list_videos

HERE = Path(__file__).resolve().parent


def legendas_do_video(svc, video_id):
    """Retorna lista de códigos de idioma das legendas existentes no vídeo."""
    try:
        resp = svc.captions().list(part="id,snippet", videoId=video_id).execute()
        idiomas = []
        for cap in resp.get("items", []):
            snip = cap.get("snippet", {})
            idiomas.append(snip.get("language", ""))
        return idiomas
    except Exception as e:
        return ["ERRO: %s" % e]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limiar", type=int, default=50,
                    help="limite de views (padrao 50)")
    ap.add_argument("--apagar", action="store_true",
                    help="apaga de fato do canal PT (sem isso so mostra)")
    ap.add_argument("--dry-run", action="store_true", help="só mostra")
    a = ap.parse_args()

    limiar = a.limiar
    fazer_apagar = a.apagar and not a.dry_run

    print("=" * 70)
    print("CANAL PT — vídeos com < %d views em inglês/espanhol (por legendas)" % limiar)
    print("=" * 70)
    print()

    svc_pt = service_for("pt")
    vids = list_videos(svc_pt)

    candidatos = []
    for v in vids:
        views = int(v.get("views", 0) or 0)
        if views >= limiar:
            continue
        vid = v["video_id"]
        titulo = v.get("title", "")
        lang = v.get("default_language", "")
        idiomas_legenda = legendas_do_video(svc_pt, vid)
        time.sleep(0.3)  # não bombardear a API

        # Considera como EN/ES se tiver legenda nesses idiomas
        # ou se o idioma do vídeo já é en/es
        eh_en = ("en" in idiomas_legenda or "en-US" in idiomas_legenda
                 or lang.startswith("en"))
        eh_es = ("es" in idiomas_legenda or "es-ES" in idiomas_legenda
                 or lang.startswith("es"))

        if eh_en or eh_es:
            candidatos.append({
                "video_id": vid,
                "titulo": titulo,
                "views": views,
                "lang_video": lang,
                "legendas": idiomas_legenda,
                "idioma_detectado": "EN" if eh_en and not eh_es else (
                    "ES" if eh_es and not eh_en else "EN+ES"),
            })

    print("Vídeos no canal PT com < %d views e legenda em EN ou ES: %d\n" % (limiar, len(candidatos)))

    for c in candidatos:
        print("  %s | %s views | %s | %s" % (
            c["video_id"], c["views"], c["idioma_detectado"], c["titulo"][:70]))
        print("      idioma vídeo: %s | legendas: %s" % (
            c["lang_video"], ", ".join(c["legendas"])))

    if candidatos and fazer_apagar:
        print("\n>>> APAGANDO do canal PT...")
        apagados, falharam = [], []
        for c in candidatos:
            try:
                svc_pt.videos().delete(id=c["video_id"]).execute()
                print("    APAGADO: %s (%s views, %s)" % (
                    c["video_id"], c["views"], c["idioma_detectado"]))
                apagados.append(c)
            except Exception as e:
                print("    FALHA ao apagar %s: %s" % (c["video_id"], e))
                falharam.append(c)
        print("\n>>> Apagados: %d | Falharam: %d" % (len(apagados), len(falharam)))
    elif candidatos:
        print("\n(Dry-run — nada foi apagado. Use --apagar para excluir de fato.)")

    print("\n" + "=" * 70)
    print("VARREDURA CONCLUÍDA")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
