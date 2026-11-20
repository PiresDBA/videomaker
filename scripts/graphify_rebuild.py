# -*- coding: utf-8 -*-
"""
Rebuild determinístico do grafo de conhecimento (graphify-out/) sem LLM.

Regra do projeto (MANUAL_GRAFOS.md §58.10): o grafo é a memória viva do repositório.
Este script existe para que o rebuild seja reprodutível e barato em token:

  python scripts/graphify_rebuild.py

Lê graphify-out/.graphify_build.json:
  {"code_only": true, "excludes": ["log_*.txt", "_dublagem_tmp*"], "gitignore": true}

O que faz:
  1. detect() com os excludes (remove logs e temporários — ilhas desconectadas)
  2. AST de todos os arquivos de código (sem LLM)
  3. semântico vazio (code_only)
  4. build + cluster + analyze
  5. rótulos determinísticos: NÓS EXTERNOS (source_file vazio, ex.: re/json/numpy)
     NÃO podem nomear comunidades — isso gerava perguntas enganosas como
     "parse_json() liga llm.py a ast/classify e eval/save" (eram bibliotecas).
  6. graph.json + GRAPH_REPORT.md + graph.html + manifest + cost
"""
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "graphify-out"
PY = sys.executable


def load(name, default):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.exists() else default


def main():
    cfg = load(".graphify_build.json", {"code_only": True, "excludes": [], "gitignore": True})
    excludes = cfg.get("excludes", [])
    code_only = cfg.get("code_only", True)
    gitignore = cfg.get("gitignore", True)
    print(f"[rebuild] root={ROOT} excludes={excludes} code_only={code_only}")

    from graphify.detect import detect, save_manifest
    from graphify.extract import collect_files, extract
    from graphify.build import build_from_json
    from graphify.cluster import cluster, score_all
    from graphify.analyze import god_nodes, surprising_connections, suggest_questions
    from graphify.report import generate
    from graphify.export import to_json

    # 1) detecção com excludes
    detected = detect(ROOT, extra_excludes=excludes, gitignore=gitignore, cache_root=OUT)
    (OUT / ".graphify_detect.json").write_text(json.dumps(detected, ensure_ascii=False), encoding="utf-8")
    print(f"[rebuild] corpus: {detected['total_files']} arquivos")

    # 2) AST
    code_files = []
    for f in detected.get("files", {}).get("code", []):
        p = Path(f)
        code_files.extend(collect_files(p) if p.is_dir() else [p])
    ast = extract(code_files, cache_root=ROOT, root=ROOT) if code_files else {
        "nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0
    }
    (OUT / ".graphify_ast.json").write_text(json.dumps(ast, ensure_ascii=False), encoding="utf-8")
    print(f"[rebuild] AST: {len(ast['nodes'])} nós, {len(ast['edges'])} arestas")

    # 3) semântico vazio (code-only: nenhum LLM, nenhuma transcrição)
    sem = {"nodes": [], "edges": [], "hyperedges": [], "input_tokens": 0, "output_tokens": 0}
    (OUT / ".graphify_semantic.json").write_text(json.dumps(sem, ensure_ascii=False), encoding="utf-8")

    seen = {n["id"] for n in ast["nodes"]}
    nodes = list(ast["nodes"])
    for n in sem["nodes"]:
        if n["id"] not in seen:
            nodes.append(n); seen.add(n["id"])
    extraction = {
        "nodes": nodes,
        "edges": ast["edges"] + sem["edges"],
        "hyperedges": sem.get("hyperedges", []),
        "input_tokens": sem.get("input_tokens", 0),
        "output_tokens": sem.get("output_tokens", 0),
    }
    (OUT / ".graphify_extract.json").write_text(json.dumps(extraction, ensure_ascii=False), encoding="utf-8")

    # 4/5) build + cluster + rótulos determinísticos
    G = build_from_json(extraction, root=ROOT, directed=False)
    if G.number_of_nodes() == 0:
        raise SystemExit("ERRO: grafo vazio")
    communities = cluster(G)
    cohesion = score_all(G, communities)
    by_id = {n["id"]: n for n in nodes}

    def clean(label):
        s = re.sub(r"\(\)$", "", str(label or "")).strip()
        s = re.sub(r'[<>:"/\\|?*]', " ", s)
        return s[:28]

    def source_group(n):
        s = str(n.get("source_file") or "").replace("\\", "/")
        if not s:
            return ""
        parts = s.split("/")
        if parts[0] in ("scripts", "earshot-sfx", "VoiceCraft-portable", "ui", "projects", "artifacts", ".githooks", "server"):
            return parts[0] if len(parts) < 3 else "/".join(parts[:2])
        return "(root)"

    labels = {}
    for cid, ids in communities.items():
        # REGRA: nós externos (sem source_file) nunca nomeiam comunidade.
        real = [by_id[i] for i in ids if i in by_id and by_id[i].get("source_file")]
        if not real:
            labels[cid] = "Bibliotecas externas (sem codigo-fonte)"
            continue
        ranked = sorted(real, key=lambda n: n.get("degree", 0) or 0, reverse=True)
        groups = Counter(source_group(n) for n in real)
        group = groups.most_common(1)[0][0]
        top = clean(ranked[0].get("label", ""))
        second = clean(ranked[1].get("label", "")) if len(ranked) > 1 else ""
        name = f"{top} / {second}" if second and second != top else top
        if group and group != "(root)":
            name = f"{group}: {name}"
        labels[cid] = name[:48]

    tokens = {"input": extraction.get("input_tokens", 0), "output": extraction.get("output_tokens", 0)}
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)
    questions = suggest_questions(G, communities, labels)

    # 6) saídas
    wrote = to_json(G, communities, str(OUT / "graph.json"), force=True, community_labels=labels)
    print(f"[rebuild] graph.json: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas, {len(communities)} comunidades (force={wrote})")
    detection_alias = {
        "files": detected.get("files", {}),
        "all_files": detected.get("files", {}),
        "total_files": detected.get("total_files", 0),
        "total_words": detected.get("total_words", 0),
        "skipped_sensitive": detected.get("skipped_sensitive", []),
        "needs_graph": True,
    }
    report = generate(G, communities, cohesion, labels, gods, surprises, detection_alias,
                      tokens, ROOT, suggested_questions=questions)
    (OUT / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    (OUT / ".graphify_labels.json").write_text(
        json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / ".graphify_analysis.json").write_text(json.dumps({
        "communities": {str(k): v for k, v in communities.items()},
        "cohesion": {str(k): v for k, v in cohesion.items()},
        "gods": gods, "surprises": surprises, "questions": questions,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    subprocess.run([PY, "-m", "graphify", "export", "html"], cwd=ROOT, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # manifest + custo
    from graphify.cli import _stamped_manifest_files
    manifest = _stamped_manifest_files(detected.get("files", {}), extraction, ROOT, partial_source_files=set())
    save_manifest(manifest, root=ROOT, scan_corpus={f for fl in detected.get("files", {}).values() for f in fl})
    cost_path = OUT / "cost.json"
    cost = json.loads(cost_path.read_text(encoding="utf-8")) if cost_path.exists() else {
        "runs": [], "total_input_tokens": 0, "total_output_tokens": 0}
    cost["runs"].append({
        "date": datetime.now(timezone.utc).isoformat(),
        "input_tokens": tokens["input"], "output_tokens": tokens["output"],
        "files": detected.get("total_files", 0),
    })
    cost_path.write_text(json.dumps(cost, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[rebuild] custo: {tokens['input']} in / {tokens['output']} out tokens (sem LLM)")

    # ATENCAO: .graphify_analysis.json e versionado — NAO apagar no cleanup.
    for name in (".graphify_detect.json", ".graphify_extract.json", ".graphify_ast.json",
                 ".graphify_semantic.json", ".needs_update"):
        (OUT / name).unlink(missing_ok=True)
    print("[rebuild] concluido")


if __name__ == "__main__":
    main()
