# -*- coding: utf-8 -*-
"""
Re-renderiza todos os projetos de video removendo todo texto da tela.
Resultado: apenas imagem + narracao (som em portugues do Brasil).
Uso:
  python scripts/rerender_all_no_text.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECTS = ROOT / "projects"
SCRIPTS = HERE


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def get_final_videos(project_dir):
    output_dir = project_dir / "output"
    if not output_dir.exists():
        return []
    videos = []
    for f in sorted(output_dir.iterdir()):
        if f.suffix.lower() != ".mp4":
            continue
        name_lower = f.name.lower()
        if "bgm" in name_lower:
            continue
        if "sem-chips" in name_lower or "old-v2" in name_lower:
            continue
        if "renders" in str(f):
            continue
        videos.append(f)
    return videos


def regenerate_scene_htmls(project_dir):
    """Regenera os scene htmls (agora vazios - sem texto na tela)."""
    script_file = project_dir / "artifacts" / "script.json"
    scenes_json = project_dir / "artifacts" / "scenes.json"
    scenes_dir = project_dir / "scenes"

    if not script_file.exists() or not scenes_json.exists():
        print(f"  AVISO: script.json ou scenes.json ausente em {project_dir.name}")
        return False

    cmd = [
        sys.executable, str(SCRIPTS / "generate_scene_htmls.py"),
        "--script", str(script_file),
        "--scenes", str(scenes_json),
        "--out-dir", str(scenes_dir),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ERRO ao gerar scene_htmls para {project_dir.name}: {r.stderr}")
        return False
    print(f"  OK: scene_htmls regenerados (sem texto) para {project_dir.name}")
    return True


def reset_phases(project_dir, phases):
    """Reseta as fases especificar no projeto."""
    project_json = project_dir / "project.json"
    if not project_json.exists():
        print(f"  AVISO: project.json ausente em {project_dir.name}")
        return False
    state = load_json(project_json)
    if "phases" not in state:
        state["phases"] = {}
    for ph in phases:
        state["phases"][ph] = {"done": False, "ts": "", "detail": ""}
    with open(project_json, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"  OK: fases resetadas: {', '.join(phases)}")
    return True


def run_pipeline(project_slug, from_phase="scenes"):
    """Roda o pipeline para o projeto a partir de uma fase."""
    cmd = [
        sys.executable, str(SCRIPTS / "pipeline.py"),
        "full",
        "--slug", project_slug,
        "--from", from_phase,
        "--skip-check",
    ]
    print(f"\n{'='*60}")
    print(f"Renderizando: {project_slug} (a partir da fase: {from_phase})")
    print(f"{'='*60}\n")
    r = subprocess.run(cmd, cwd=str(ROOT))
    return r.returncode == 0


def main():
    if not PROJECTS.exists():
        print(f"ERRO: pasta de projetos nao encontrada: {PROJECTS}")
        return 1

    projects = sorted([p for p in PROJECTS.iterdir() if p.is_dir()])
    print(f"Encontrados {len(projects)} projeto(s)\n")

    ok_count = 0
    fail_count = 0
    skip_count = 0

    for pdir in projects:
        videos = get_final_videos(pdir)
        if not videos:
            print(f"PULANDO {pdir.name}: sem video final em output/")
            skip_count += 1
            continue

        # 1. Regenerar scene_htmls (sem texto)
        if not regenerate_scene_htmls(pdir):
            fail_count += 1
            continue

        # 2. Resetar fases scenes, compose, preprocess, render
        if not reset_phases(pdir, ["scenes", "compose", "preprocess", "render"]):
            fail_count += 1
            continue

        # 3. Rodar pipeline a partir de scenes
        success = run_pipeline(pdir.name, from_phase="scenes")
        if success:
            ok_count += 1
            print(f"\nSUCESSO: {pdir.name} renderizado sem texto na tela")
        else:
            fail_count += 1
            print(f"\nFALHA: {pdir.name} nao foi renderizado com sucesso")

    print(f"\n{'='*60}")
    print(f"RESULTADO FINAL: {ok_count} sucesso(s), {fail_count} falha(s), {skip_count} pulado(s)")
    print(f"{'='*60}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
