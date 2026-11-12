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
| narração duplicada / frase do coração | §46 |
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
  é o zoológico). **Exceção única:** vídeo de passeio por vários lugares reais —
  aí cada seção acontece em um lugar diferente, na ordem pedida
  (`MANUAL_GRAFOS.md` §47).
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

Ao trocar de assunto/slug, resetar **`scenes` junto com `images`** para zerar o
cenário (`image_prompts.json` é gerado na fase `scenes`). A consistência vale
apenas dentro do mesmo vídeo/projeto; nunca reaproveitar cenário de vídeo anterior.

---

## 5.2. Regra de narração (anti-duplicação + encerramento humano)

- A narração **nunca pode sair duplicada**. O gerador Gemini verifica o áudio com
  `faster-whisper` e regenera, ou sintetiza frase a frase, se detectar repetição
  (`MANUAL_GRAFOS.md` §46.3).
- O encerramento (`s_outro`) não pode usar frases não humanas como
  "no nosso coração" / "acompanhe nosso coração". Quando falar de coração, usar
  sempre: **"Um grande beijo no seu coração e fique com a gente! Acompanhe nossos
  próximos vídeos!"** (§46.4).
- Implementação: `scripts/gen_narration_gemini_sections.py` e
  `scripts/narration_contract.py` (fonte única da frase).

---

## 5.3. Narração multi-idioma (pt → en/es)

- Inglês (`en`) e espanhol (`es`) geram narração com **Gemini TTS (Google AI Studio)**
  via `scripts/gen_narration_gemini_sections.py --lang <en|es>`, com vozes nativas
  (`Achernar` para inglês, `Leda` para espanhol) e mapa de pronúncia
  (`Luninha → little luna` em en, `lunita` em es).
- Português (`pt`) continua com Edge-TTS local (inalterado).
- Quando o Gemini TTS não tem cota (HTTP 429 em todas as chaves), o pipeline faz
  **fallback automático para Edge-TTS local** (`gen_narration_edge.py`).
- Saída por idioma: `assets/audio/narration/<lang>/sN.wav` e
  `artifacts/narration_timing_<lang>.json`.

---

## 5.4. Título da capa no idioma do vídeo

- `scripts/build_composition.py` aceita flag `--lang` e lê o título de
  `artifacts/script_<lang>.json` (fallback `script.json`) para o `<h1 id="intro-title">`
  da capa/saudação `s0`. Assim a abertura fica escrita na mesma língua da narração.
- `scripts/pipeline.py` (`phase_compose`) passa `--lang <mix-lang>` ao construtor.

---

## 5.5. Estratégia de trabalho: disco rápido (C:) + histórico lento (E:)

- **Disco de trabalho (rápido):** `C:\videomaker\projects` (SSD).
- **Disco histórico (lento):** `E:\videomaker\projects` (arquivo de verdade).
- **Fluxo por projeto (loop pt → en/es):**
  1. Copiar o projeto de `E:` para `C:\videomaker\projects\`.
  2. Processar en/es em `C:` (tradução local via `translate_local.py`,
     narração com fallback Edge-TTS, timeline, mix, composição, render via
     `loop_publicacao.py`).
  3. Quando en/es estiverem completos (MP4s gerados), copiar de volta para
     `E:\videomaker\projects\`, sobrescrevendo o histórico.
  4. Registrar na `LISTA_PUBLICACAO.md` os projetos com en/es completos.
  5. Atualizar `LOG_PROGRESSO_MULTILANG.md` com o que foi feito.
- Nunca trabalhar diretamente no `E:` (disco lento inviabiliza o loop de render).

---

## 5.6. Lista de publicação

- Todo projeto que ficar com en/es completos (MP4s gerados) deve ser registrado
  em `LISTA_PUBLICACAO.md` (raiz do Videomaker), pronto para upload ao YouTube
  com metadados no idioma correto (título, descrição, tags, idioma do áudio e
  legendas por idioma).
- Não publicar antes de ter os 3 idiomas (pt + en + es) renderizados.

---

## 6. Resumo em 30 segundos

1. Ler `CONTRATO.md` + `MANUAL_GRAFOS.md` + docstring do `pipeline.py`.
2. Criar branch com nome curto e óbvio.
3. Fazer a mudança **e** atualizar o `MANUAL_GRAFOS.md` no mesmo commit.
4. Rodar os checks.
5. Commit + push da branch.

**O manual é a memória do produto. Se não está no manual, não existe.**
