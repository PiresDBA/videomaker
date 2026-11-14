# AGENTS.md — Videomaker

**Leia `CONTRATO.md` e `MANUAL_GRAFOS.md` ANTES de fazer qualquer coisa.**
O manual é a fonte de verdade do produto: o que já está feito, como está e por
quê. Não refaça e não desfaça o que já está resolvido.

| Arquivo | Ler quando |
|---------|-----------|
| `CONTRATO.md` | sempre, primeiro (regras de trabalho) — ver §5.8 antes de mexer em imagem |
| `MANUAL_GRAFOS.md` | sempre (estado do produto, grafo, decisões) — ver §58.6 |
| `scripts/topics.txt` | ao criar vídeo novo (tema obrigatório, §5.11) |
| `scripts/pipeline.py` (topo) | antes de mexer no pipeline (comandos e argumentos) |
| `AGENTS.md` (este) | para o resumo de 30 segundos |

## ⛔ PARE — trava antes do erro (leia antes de gerar imagem/prompt)

O bug mais caro do projeto (Chihuahua e Restaurante com a **mesma figura
repetida**) voltou duas vezes. Se você for tocar em **prompt de imagem**,
**flow_fetch**, **cenas**, **`scene_mode`** ou **render**, responda estas
perguntas **antes** de escrever código:

1. **Estou pedindo para o modelo copiar a referência?** Se a frase for "siga a
   referência para tudo", "mesma aparência em todas as imagens", "mantenha este
   mesmo ambiente", "igual à imagem anterior" → **PROIBIDO**. A referência é só
   design das personagens + estilo do traço. **A cena manda em tudo.**
2. **Cada pausa de narração tem uma imagem própria e diferente?** Se duas
   pausas mostram a mesma figura, o vídeo está errado.
3. **O prompt tem o bloco "REGRA ANTI-REPETICAO"** (cena nova, novo
   enquadramento, novo ângulo, novas poses)?
4. **`scene_density.scene_mode` continua `two`?** `beats` gera 3–4 prompts quase
   idênticos por seção e multiplica a repetição. Não trocar sem prova.
5. **Imagem é só Google Flow.** Gemini **nunca** gera imagem. Se o Flow falhar,
   pare e avise o usuário.
6. **Estou desligando/contornando uma trava?** (apagar chamada `trava()`, rodar
   `git commit --no-verify`, usar `--skip-check`) → **NÃO**. Se a trava falhou,
   o problema é o prompt/imagem.
7. **Estou gerando imagem para outro idioma?** → **NÃO**. As imagens são
   geradas **uma vez** (em PT) e PT/EN/ES usam os mesmos arquivos. Por idioma
   mudam só tradução, overlays, narração, legendas, mixagem e render
   (`CONTRATO.md` §5.9).
8. **Estou reaproveitando um MP4 antigo?** → só se ele for **mais novo** que
   as imagens/roteiro/overlays/narração. Imagem nova + MP4 velho = vídeo
   errado publicado (§5.10).

Se qualquer resposta for "sim, estou fazendo isso" → **pare e conserte antes**.
Detalhes: `CONTRATO.md` §5.8 e `MANUAL_GRAFOS.md` §58.6.

## Regras mínimas

1. **Branch antes de mexer**: `git checkout -b feature/nome-curto`.
2. **O `MANUAL_GRAFOS.md` vai no mesmo commit da mudança**. Se mudou fluxo,
   fase, dependência, CLI ou regra → atualize §3, §4, §30.7, §36, §37 ou crie
   uma seção nova.
3. **Push só depois do manual**: branch → código → manual → checks → commit → push.
4. **Nunca commitar segredos** (`.env`, `client_secret*.json`, `youtube_token.json`,
   `scripts/config.json` já ignorados).
5. **Rodar antes do push**: `python scripts/check_manual.py`,
   `python scripts/check_prompt_repeticao.py`, `python scripts/check_imagens_repetidas.py`,
   `python scripts/check_texto_idioma.py`, `python scripts/check_topico_novo.py`
   e os smoke tests.
6. **Não usar `git commit/push --no-verify`** para furar os hooks. Se o hook
   barrou, conserte o motivo (é para isso que ele existe).
7. **Vídeo novo sai da fila `scripts/topics.txt`**: leia a lista, sorteie com
   `python scripts/select_topic.py`, confira duplicidade e registre o tema
   usado. Nunca reformate nem apague a lista (`CONTRATO.md` §5.11).

## Comandos úteis

```powershell
python scripts/pipeline.py --help          # comandos e argumentos
python scripts/pipeline.py status --slug <slug>   # estado de um projeto
python scripts/check_manual.py              # manual em dia com o código?
python scripts/check_projects.py            # descrições dos projetos no padrão
python scripts/check_prompt_repeticao.py    # prompt manda copiar a referência?
python scripts/check_prompt_repeticao.py --strict   # + estrutura nova (CENA + anti-repetição)
python scripts/check_imagens_repetidas.py   # duas cenas são a mesma figura?
python scripts/check_imagens_compartilhadas.py --slug <slug>   # PT/EN/ES usam as mesmas imagens?
python scripts/check_texto_idioma.py        # PT/recusa do Gemini em script EN/ES?
python scripts/select_topic.py              # sorteia tema novo de scripts/topics.txt
python scripts/check_topico_novo.py --tema "..."   # tema repetido? (fila)
python scripts/install_hooks.py             # instala .githooks (uma vez por clone)
```

## Hooks (instalar uma vez por clone)

```powershell
python scripts/install_hooks.py
```

Ativa `.githooks/pre-commit` e `.githooks/pre-push`: sintaxe Python, trava de
prompt, trava de imagem repetida e `check_manual.py`. Não desative.

Detalhes: `CONTRATO.md`.
