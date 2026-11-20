---
type: "query"
date: "2026-11-20T11:34:29.593392+00:00"
question: "Por que parse_json() liga llm.py a testes, ast/classify e eval/save?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["parse_json()", "llm.py", "_outer_object()", "critique()"]
---

# Q: Por que parse_json() liga llm.py a testes, ast/classify e eval/save?

## Answer

Expandido via vocab: [llm, check, tests, critique, ast, classify, eval, collections, save, json, prompt]. parse_json() esta em earshot-sfx/earshot/llm.py:316, grau 7, 4 comunidades. Corpo: remove code fences, tenta _outer_object(), remove virgulas finais, json.loads, retorna dict ou None. Arestas EXTRACTED: chama critique() (tests: build_prompt/critique), re (alocado em scripts: ast/classify), _outer_object() (propria comunidade), json (alocado em eval: collections/save), e e testada por test_parse_json_and_normalize(). PONTO CRITICO: as conexoes com ast/classify e eval/save sao nos de biblioteca padrao (re, json) clusterizados em comunidades arbitrarias — nao acoplamento real com esses subsistemas. O verdadeiro acoplamento e intra-arquivo (critique, _outer_object). Sem bypass encontrado. A premissa 'ponte entre comunidades' do relatorio e enganosa: e ponte para bibliotecas, nao para subsistemas.

## Outcome

- Signal: useful

## Source Nodes

- parse_json()
- llm.py
- _outer_object()
- critique()