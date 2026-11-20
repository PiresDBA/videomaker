---
type: "query"
date: "2026-11-20T11:34:28.854619+00:00"
question: "Por que active_length() conecta compare.py, resample/features.py, align/onset e to_mono/get?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["active_length()", "to_mono()", "frame_rms()", "compare.py"]
---

# Q: Por que active_length() conecta compare.py, resample/features.py, align/onset e to_mono/get?

## Answer

Expandido via vocab: [compare, resample, features, align, onset, get, earshot, length, mono, sample, trim]. active_length() esta em earshot-sfx/earshot/compare.py:69 e tem grau 6, com 4 comunidades tocadas. Todas as arestas sao EXTRACTED (calls): chama to_mono() (audio.py -> comunidade to_mono/get), frame_rms() (features.py -> resample/features.py) e numpy (que o grafo alocou em tests: align/onset). O corpo e frame_rms(audio.to_mono(x), int(0.01*SR)), seleciona frames dentro de floor_db=40 do pico e devolve a duracao em s. A ponte e dependencia real de codigo de 3 linhas, nao inferencia. Nota: a comunidade 'align/onset' para numpy e artefato de clusterizacao de no de biblioteca; nao representa logica de align/onset. Bypass: eval/semantics/run_eval.py:574 usa a mesma constante 0.01*SR sem aresta, mas so calcula offset de indice, nao reimplementa active_length().

## Outcome

- Signal: useful

## Source Nodes

- active_length()
- to_mono()
- frame_rms()
- compare.py