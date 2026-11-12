# -*- coding: utf-8 -*-
"""
Varredura: compara o canal principal (PT) com os canais EN e ES.

Para cada vídeo no canal PT que tem equivalente em EN ou ES (casado por
duração — o mais confiável, já que títulos/descrições foram editados):
  - Se o equivalente em EN/ES ESTÁ publicado no canal certo
  - E o vídeo no canal PT tem MENOS de --limiar-views visualizações
  → Apaga do canal PT

Uso:
  python scripts/limpar_duplicados_pt.py --limiar-views 100 --apagar
  python scripts/limpar_duplicados_pt.py --limiar-views 100 --dry-run   (só mostra o que faria)
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from listar_canal import service_for, list_videos, iso_para_segundos

HERE = Path(__file__).resolve().parent
LIMIAR_PADRAO = 100


def casamento_por_duracao(videos_canal, duracao_ref, tolerancia=5.0):
    """Retorna vídeos do canal cuja duração bate com duracao_ref."""
    if not duracao_ref:
        return []
    achados = []
    for v in videos_canal:
        try:
            d = float(v.get("duration_s", 0) or 0)
        except Exception:
            continue
        if abs(d - duracao_ref) <= tolerancia:
            achados.append(v)
    return achados


def extrair_duracao_local(proj_dir, lang):
    """Duracao do MP4 local em segundos."""
    import subprocess as sp
    nome = f"{proj_dir.name}_{lang}.mp4"
    mp4 = proj_dir / "output" / nome
    if not mp4.is_file():
        mp4 = proj_dir / "output" / f"{proj_dir.name}.mp4"
    if not mp4.is_file():
        return None
    try:
        r = sp.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp4)],
            capture_output=True, text=True, timeout=60)
        return float((r.stdout or "0").strip() or 0)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limiar-views", type=int, default=LIMIAR_PADRAO,
                    help="apaga do PT se tiver menos views que isso (padrao 100)")
    ap.add_argument("--apagar", action="store_true",
                    help="apaga de fato (sem isso so mostra o que faria)")
    ap.add_argument("--dry-run", action="store_true", help="só mostra, não apaga")
    a = ap.parse_args()

    limiar = a.limiar_views
    fazer_apagar = a.apagar and not a.dry_run

    print("=" * 70)
    print("VARREDURA: canal PT vs canais EN e ES")
    print("=" * 70)
    print(f"Limiar de views: {limiar} (apaga do PT se < {limiar} views)")
    print(f"Modo: {'APAGAR DE FATO' if fazer_apagar else 'APENAS MOSTRAR (dry-run)'}")
    print()

    # Lista os 3 canais
    canais = {}
    for lang in ("pt", "en", "es"):
        try:
            svc = service_for(lang)
            vids = list_videos(svc)
            canais[lang] = vids
            print(f"Canal {lang.upper()}: {len(vids)} vídeos lidos")
        except SystemExit as e:
            print(f"Canal {lang.upper()}: ERRO — {e}")
            canais[lang] = []
        except Exception as e:
            print(f"Canal {lang.upper()}: ERRO — {e}")
            canais[lang] = []

    print()

    # Para cada vídeo no canal PT, procura equivalente em EN e ES por duração
    apagar_pt = []
    manter_pt = []
    sem_equivalente = []

    for v_pt in canais.get("pt", []):
        vid_pt = v_pt["video_id"]
        titulo_pt = v_pt.get("title", "")
        views_pt = int(v_pt.get("views", 0) or 0)
        dur_pt = float(v_pt.get("duration_s", 0) or 0)

        # Procura equivalente em EN e ES por duração
        eq_en = casamento_por_duracao(canais.get("en", []), dur_pt)
        eq_es = casamento_por_duracao(canais.get("es", []), dur_pt)

        tem_en = len(eq_en) > 0
        tem_es = len(eq_es) > 0

        if not (tem_en or tem_es):
            sem_equivalente.append((vid_pt, titulo_pt, views_pt, dur_pt))
            continue

        # Tem equivalente em pelo menos um canal estrangeiro
        info = []
        if tem_en:
            info.append(f"EN: {eq_en[0]['video_id']} ({eq_en[0].get('views',0)} views)")
        if tem_es:
            info.append(f"ES: {eq_es[0]['video_id']} ({eq_es[0].get('views',0)} views)")

        if views_pt < limiar:
            apagar_pt.append({
                "video_id": vid_pt,
                "titulo": titulo_pt,
                "views": views_pt,
                "duracao": dur_pt,
                "equivalentes": info,
            })
        else:
            manter_pt.append({
                "video_id": vid_pt,
                "titulo": titulo_pt,
                "views": views_pt,
                "duracao": dur_pt,
                "equivalentes": info,
            })

    print(f"Vídeos no canal PT com equivalente EN/ES e < {limiar} views: {len(apagar_pt)}")
    print(f"Vídeos no canal PT com equivalente EN/ES e >= {limiar} views (mantém): {len(manter_pt)}")
    print(f"Vídeos no canal PT sem equivalente EN/ES: {len(sem_equivalente)}")
    print()

    if apagar_pt:
        print("--- VÍDEOS DO CANAL PT CANDIDATOS À EXCLUSÃO ---")
        for item in apagar_pt:
            print(f"  {item['video_id']} | {item['views']} views | {item['duracao']}s")
            print(f"      {item['titulo'][:80]}")
            for eq in item['equivalentes']:
                print(f"      -> {eq}")
        print()

        if fazer_apagar:
            print(">>> APAGANDO do canal PT...")
            svc_pt = service_for("pt")
            apagados = []
            falharam = []
            for item in apagar_pt:
                try:
                    svc_pt.videos().delete(id=item["video_id"]).execute()
                    print(f"    APAGADO: {item['video_id']} ({item['views']} views)")
                    apagados.append(item)
                except Exception as e:
                    print(f"    FALHA ao apagar {item['video_id']}: {e}")
                    falharam.append(item)
            print(f"\n>>> Apagados: {len(apagados)} | Falharam: {len(falharam)}")
        else:
            print("(Dry-run — nada foi apagado. Use --apagar para excluir de fato.)")

    if manter_pt:
        print("\n--- VÍDEOS DO CANAL PT MANTIDOS (>= limiar de views) ---")
        for item in manter_pt[:10]:
            print(f"  {item['video_id']} | {item['views']} views | {item['titulo'][:60]}")
        if len(manter_pt) > 10:
            print(f"  ... e mais {len(manter_pt) - 10}")

    if sem_equivalente:
        print(f"\n--- VÍDEOS DO CANAL PT SEM EQUIVALENTE EN/ES ({len(sem_equivalente)}) ---")
        for vid_pt, tp, views, dur in sem_equivalente[:10]:
            print(f"  {vid_pt} | {views} views | {tp[:60]}")
        if len(sem_equivalente) > 10:
            print(f"  ... e mais {len(sem_equivalente) - 10}")

    print("\n" + "=" * 70)
    print("VARREDURA CONCLUÍDA")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
