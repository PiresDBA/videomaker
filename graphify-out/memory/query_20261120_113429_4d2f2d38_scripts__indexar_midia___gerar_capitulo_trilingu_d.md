---
type: "query"
date: "2026-11-20T11:34:29.350674+00:00"
question: "scripts: indexar_midia / gerar_capitulo_trilingu deveria ser dividido?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["gerar_capitulo_trilinguo.py", "pipeline.py", "hook_manager.py"]
---

# Q: scripts: indexar_midia / gerar_capitulo_trilingu deveria ser dividido?

## Answer

Expandido via vocab: [indexar, midia, gerar, capitulo, scripts, modulo, split, seed, chapter]. Comunidade tem 176 nos: 133 de scripts/pipeline.py, 31 de gerar_capitulo_trilinguo.py, 9 de hook_manager.py, 3 sem src. Densidade 0.0218 (= coesao 0.022 do relatorio), um unico componente conectado. Acoplamento real entre arquivos: 14 arestas gerar_capitulo<->pipeline, 4 hook_manager<->pipeline. Os 3 arquivos formam uma unidade coerente de orquestracao. A baixa coesao vem de pipeline.py ser um 'god file' com 133 funcoes/fases frouxamente ligadas, NAO de modulos distintos. O rotulo automatico e enganoso: nomeado apos 2 nos topo (indexar_midia, gerar_capitulo), mas 76% da comunidade e pipeline.py. Recomendacao: nao dividir a comunidade; dividir pipeline.py em modulos por fase — ai sim a coesao sobe e o gerador trilinguo vira sua propria comunidade.

## Outcome

- Signal: useful

## Source Nodes

- gerar_capitulo_trilinguo.py
- pipeline.py
- hook_manager.py