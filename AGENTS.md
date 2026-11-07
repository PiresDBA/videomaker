# AGENTS.md — Videomaker

**Leia `CONTRATO.md` e `MANUAL_GRAFOS.md` ANTES de fazer qualquer coisa.**
O manual é a fonte de verdade do produto: o que já está feito, como está e por
quê. Não refaça e não desfaça o que já está resolvido.

| Arquivo | Ler quando |
|---------|-----------|
| `CONTRATO.md` | sempre, primeiro (regras de trabalho) |
| `MANUAL_GRAFOS.md` | sempre (estado do produto, grafo, decisões) |
| `scripts/pipeline.py` (topo) | antes de mexer no pipeline (comandos e argumentos) |
| `AGENTS.md` (este) | para o resumo de 30 segundos |

## Regras mínimas

1. **Branch antes de mexer**: `git checkout -b feature/nome-curto`.
2. **O `MANUAL_GRAFOS.md` vai no mesmo commit da mudança**. Se mudou fluxo,
   fase, dependência, CLI ou regra → atualize §3, §4, §30.7, §36, §37 ou crie
   uma seção nova.
3. **Push só depois do manual**: branch → código → manual → checks → commit → push.
4. **Nunca commitar segredos** (`.env`, `client_secret*.json`, `youtube_token.json`,
   `scripts/config.json` já ignorados).
5. **Rodar antes do push**: `python scripts/check_manual.py` e os smoke tests.

## Comandos úteis

```powershell
python scripts/pipeline.py --help          # comandos e argumentos
python scripts/pipeline.py status --slug <slug>   # estado de um projeto
python scripts/check_manual.py              # manual em dia com o código?
python scripts/check_projects.py            # descrições dos projetos no padrão
```

Detalhes: `CONTRATO.md`.
