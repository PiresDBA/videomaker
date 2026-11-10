# CONTRATO DE TRABALHO — Videomaker

> **Leia este arquivo ANTES de qualquer coisa.**
> Leia também o `MANUAL_GRAFOS.md`, que é a fonte de verdade do produto.

Este contrato existe para **não gastar tempo e token com o que já está
resolvido** e para **não desfazer o que já estava funcionando**.

---

## 1. A regra de ouro

**Antes de escrever qualquer linha de código, ler:**

1. **`CONTRATO.md`** (este arquivo) — as regras do jogo.
2. **`MANUAL_GRAFOS.md`** — o que já foi feito, como está, e por quê.
3. **`scripts/pipeline.py`** (topo do arquivo) — a referência completa de
   comandos, argumentos e fases, com exemplos.

Se algo já está documentado no manual, **já foi feito**. Não refaça.
Se algo já está documentado no manual, **não está quebrado** (salvo indication
contrária explícita). Não desfaça.

---

## 2. Onde está a documentação

| Fonte | O que tem | Como consultar |
|-------|-----------|----------------|
| `MANUAL_GRAFOS.md` | Estado do produto, grafo do pipeline, decisões, histórico | seção por seção (`## N.`) |
| `scripts/pipeline.py` (docstring do topo) | Todos os comandos, todos os argumentos, exemplos | `python scripts/pipeline.py --help` |
| `scripts/pipeline.py` (docstrings das funções) | O que cada função faz e produz | editor / busca por `def ` |
| `CONTRATO.md` (este arquivo) | Regras de trabalho | leitura inicial |
| `AGENTS.md` | Resumo de 30 segundos para agentes | leitura automática |

### 2.1. Índice rápido do manual

| Se você quer... | Vá para |
|-----------------|---------|
| o grafo do pipeline | §3 (Mermaid) e §30.7 (resumo textual) |
| as dependências entre fases | §4 |
| corrigir um bug | §10 (Solução de problemas) |
| o padrão de descrição do YouTube | §36 |
| a CLI do pipeline | §37 |
| a regra de branch/grafo/push | §38 |
| voz, música e fallback de narração | §1.7, §1.8, §34 |
| consistência de cenário e personagens | §45 |
| o executor diário | §11 |

---

## 3. O que fazer em cada mudança

```powershell
# 1) BRANCH antes de mexer em qualquer arquivo
git checkout -b feature/nome-curto-da-mudanca

# 2) código + MANUAL_GRAFOS.md atualizado (o manual sempre vai no mesmo commit)

# 3) commit + push (somente depois do manual)
git add -A
git commit -m "tipo: o que mudou"
git push -u origin feature/nome-curto-da-mudanca
```

**A ordem é obrigatória: branch → código → grafo/manual → commit → push.**

### 3.1. O manual é parte da mudança

Toda alteração precisa de um registro no `MANUAL_GRAFOS.md`:

- mudou **fluxo/fase/dependência** → §3 e §4 (grafo Mermaid) + §30.7
- mudou **CLI/argumento** → §37
- mudou **descrição do YouTube** → §3 (fase `youtube`) + §36
- mudou **narração/voz/música** → §3 + §1.7/§1.8
- mudou **regra de processo** → nova seção no fim do manual
- **não mudou o fluxo** → ainda assim registre a mudança em uma seção nova

Sem isso, o próximo vai repetir o trabalho (e gastar token) ou desfazer algo
que já estava certo.

---

## 4. Proibições (o que NÃO fazer)

1. **Não commitar segredo.** `.env`, `scripts/client_secret*.json`,
   `scripts/youtube_token.json` e `scripts/config.json` já estão no
   `.gitignore`. Verificar com `git status` antes de commitar.
2. **Não mexer em arquivo gerado.** `projects/`, `banco de imagens/`,
   `banco de musicas/`, `hyperframes-workspace/` são saída, não fonte.
3. **Não refazer o que o manual já diz que está pronto.** Se o manual diz que
   está resolvido, provavelmente está — investigue oporquê antes de alterar.
4. **Não dar `push --force`** em branch já publicada.
5. **Não mexer no `main` direto.** Toda mudança passa por branch própria.
6. **Não usar `git commit --amend`** em commit já publicado.

---

## 5. Antes de dar push

```powershell
python scripts/check_manual.py     # o manual está em dia com o código?
python scripts/smoke_test_description.py
python scripts/check_projects.py
git status
git diff
```

Se `check_manual.py` acusar desync, **corrija o manual antes de dar push**.

---

## 5.1. Regra de consistência de cenário, personagens e lição educativa

Esta é uma regra de produto obrigatória. Toda mudança que afetar a geração de roteiro
ou imagens deve respeitá-la:

- **Cenário consistente:** todo o vídeo acontece no mesmo ambiente definido pelo tema.
  Se o tema for "zoológico", todas as cenas acontecem no zoológico. Se for "Marte",
  todas as cenas acontecem em Marte (ou na nave que vai e volta da Terra). Não mudar
  de cenário aleatoriamente (não colocar grama se o tema é Marte, nem casa se o tema
  é o zoológico).
- **Personagens consistentes:** Frida (buldogue inglês) e Luna (salsicha/dachshund)
  devem manter a mesma aparência do começo ao fim do vídeo. Nunca mudar a raça, cor
  ou traço dos personagens entre cenas.
- **Lição educativa:** toda história infantil deve ensinar algo para as crianças.
  Uma lição/moral deve ficar clara na última seção de história ou na `s_final`
  (ex: "O que aprendemos hoje? Ser gentil com os outros é importante.").

Essa regra está documentada em **`MANUAL_GRAFOS.md` §45** e implementada em
`scripts/generate_scenes_and_prompts.py` (função `_extrair_cenario()` e parâmetro
`cenario` em `build_prompt()`) e
`scripts/generate_script_from_prompt.py` (SYSTEM prompt).

---

## 6. Resumo em 30 segundos

1. Ler `CONTRATO.md` + `MANUAL_GRAFOS.md` + docstring do `pipeline.py`.
2. Criar branch com nome curto e óbvio.
3. Fazer a mudança **e** atualizar o `MANUAL_GRAFOS.md` no mesmo commit.
4. Rodar os checks.
5. Commit + push da branch.

**O manual é a memória do produto. Se não está no manual, não existe.**
