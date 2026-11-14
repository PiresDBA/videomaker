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
7. **Não pedir para o gerador de imagem copiar a referência.** Nada de "siga a
   referência para tudo", "mesma aparência em todas as imagens", "mantenha este
   mesmo ambiente". A referência é só design das personagens/estilo; a cena vem
   da narração (§5.8). Foi assim que o Chihuahua e o Restaurante saíram com a
   mesma figura repetida.
7. **Não gerar imagem por idioma.** As imagens são geradas **uma vez** (em PT)
   e PT/EN/ES usam os **mesmos arquivos**; por idioma mudam só tradução,
   overlays, narração, legendas, mixagem e render (§5.9). A trava
   `check_imagens_compartilhadas.py` aborta o capítulo se a pasta de cenas
   mudar entre idiomas.
8. **Não renderizar nem publicar vídeo com imagem repetida.** Se duas pausas
   mostram a mesma figura, o vídeo está errado: corrija as imagens antes.
9. **Não desligar/contornar as travas** `check_prompt_repeticao.py`,
   `check_imagens_repetidas.py` e `check_imagens_compartilhadas.py` (nem
   remover as chamadas `trava()` do `gerar_capitulo_trilinguo.py`). Se a trava
   incomodou, o problema é o prompt/imagem.
10. **Não trocar `scene_mode` de `two` para `beats`** sem antes provar (com as
    imagens na mão) que não há repetição (§5.8).
11. **Não usar o Gemini para gerar imagem.** Imagem é só Google Flow; se o Flow
    falhar, pare e avise.

---

## 5. Antes de dar push

```powershell
python scripts/check_manual.py     # o manual está em dia com o código?
python scripts/check_prompt_repeticao.py   # prompt não manda copiar a referência?
python scripts/check_imagens_repetidas.py  # duas cenas não são a mesma figura?
python scripts/smoke_test_description.py
python scripts/check_projects.py
git status
git diff
```

Se `check_manual.py` acusar desync, **corrija o manual antes de dar push**.
As duas travas de repetição também rodam nos hooks de `git` (`.githooks/`);
se elas falharem, **não** use `--no-verify`: conserte o prompt/imagens (§5.8).

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

- Todos os idiomas (pt, en, es) geram narração com **Gemini TTS (Google AI Studio)**
  via `scripts/gen_narration_gemini_sections.py --lang <pt|en|es>`, com vozes nativas
  (`Achernar` para português e inglês, `Leda` para espanhol) e mapa de pronúncia
  (`Luninha → little luna` em en, `lunita` em es).
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

## 5.7. Metadado do YouTube no idioma do vídeo (regra dura)

- Título, gancho e enredo vêm **sempre** de `artifacts/script_<lang>.json`.
- **Proibido** traduzir título/descrição "na hora" com `gemini_fetch.py` no
  momento do upload: quando a tradução falha, o texto em português sobe para o
  canal estrangeiro. Se falta `script_<lang>.json`, o upload **aborta**.
- Cada idioma usa o **seu** canal e o **seu** token
  (`youtube_token_pt.json` / `_en.json` / `_es.json`). Ver manual §56.
- O upload respeita a cota da API (`~6 uploads/canal/dia`); ele é resumível e
  retoma no dia seguinte pelo `scripts/.publish_history_idioma.json`.
- Antes de publicar, conferir com `python scripts/listar_canal.py`.

---

## 5.8. Imagem única por pausa (regra dura — NÃO repetir a referência)

Esta seção existe porque o erro já aconteceu duas vezes (Chihuahua a partir de
~1:22 e Restaurante do início ao fim mostravam sempre a mesma figura). Leia
antes de mexer em **qualquer** texto que gere prompt de imagem.

### O que a referência pode e o que NÃO pode

A imagem passada em `--ref-image` (a cena anterior, ou o `referencia.png` do
banco) serve **só** para:

- o **design das personagens** (Frida = buldogue inglesa; Luna = salsicha);
- o **estilo do traço/iluminação** da série.

Ela **nunca** define a cena. Quem manda na cena é a **narração da pausa**.

**NUNCA escrever em prompt (nem em código que monta prompt):**

| Proibido | Por quê |
|---|---|
| "siga a imagem de referência anexada **para TUDO**" | o modelo copia a cena inteira |
| "mantenha exatamente a mesma aparência … **em todas as imagens**" | congela a figura |
| "mantenha este **mesmo ambiente** em todas as imagens" | repete cenário e enquadramento |
| "use `referencia.png` como referência de cores/estilos" | volta a ancorar no arquivo errado |
| "mesma cena", "mesmo ângulo", "igual à imagem anterior" | repetição direta |

**SEMPRE** que montar prompt:

1. A **CENA** (o que a narração diz naquela pausa) é a prioridade máxima.
2. Todo prompt leva o bloco **"REGRA ANTI-REPETICAO"**: cena nova, novo
   enquadramento, novo ângulo, novas poses, novos objetos.
3. O cenário é "o mesmo **tipo** de lugar, com enquadramento/ângulo/fundo
   diferentes em cada imagem" — nunca "o mesmo ambiente".
4. Cada pausa de narração tem **uma imagem própria e diferente**. Sem exceção.

### Travas automáticas (não desligar)

- `scripts/check_prompt_repeticao.py` — falha se um construtor de prompt ou um
  `image_prompts.json` tiver as frases proibidas. `--strict` exige também a
  estrutura nova (CENA prioridade + REGRA ANTI-REPETICAO).
- `scripts/check_imagens_repetidas.py` — compara as imagens de cena duas a duas
  (Pillow 48x48) e falha se duas forem a mesma figura.
- `scripts/gerar_capitulo_trilinguo.py` chama as duas (`trava()`) **antes** de
  gerar imagens e **antes** de renderizar: se falhar, o capítulo aborta.
- `flow_fetch.py` descarta e reenvia imagem praticamente igual à referência ou a
  qualquer imagem já existente na pasta, e ignora a miniatura da referência que
  carrega pela rede (era ela que era salva no lugar da imagem gerada).
- `scene_density.scene_mode` fica em **`two`**. O modo `beats` gera 3–4 prompts
  quase idênticos por seção e multiplica a repetição.

### Antes de renderizar e antes de publicar

```powershell
python scripts/check_prompt_repeticao.py --strict
python scripts/check_imagens_repetidas.py
```

Abra **3–4 `.jpg`** da pasta `assets/images/gemini/scenes/` e confirme que são
cenas diferentes entre si. Se houver repetição: **não renderize, não publique**.
Apague as duplicadas, regenere. Se o vídeo já subiu assim, **apague no YouTube
com o token do canal dono** e reenvie.

Documentação completa (causa, mecanismo e revisão): `MANUAL_GRAFOS.md` §58.6.

---

## 5.9. Imagens compartilhadas entre PT/EN/ES (regra dura)

As imagens de cena são geradas **uma única vez**, em português, pelo Google
Flow, e os **três idiomas usam exatamente os mesmos arquivos**
(`assets/images/gemini/scenes/*.jpg`, byte a byte).

Por idioma muda **apenas**:

| Muda por idioma | Não muda |
|---|---|
| tradução do roteiro (`script_<lang>.json`) | imagens de cena |
| overlays/capa/encerramento (`scenes/<lang>/`) | `scenes.json` / `image_prompts.json` |
| narração (`assets/audio/narration/<lang>/`) | montagem de cenas |
| legendas (`assets/subtitles/<lang>/`) | — |
| mixagem, composição, render | — |

**Proibido:**

1. Gerar imagem nova "para o EN/ES". Não existe imagem por idioma.
2. Rodar a fase de imagens de novo depois que o vídeo já tem imagens só
   porque está renderizando outro idioma.
3. Apagar/regravar a pasta de cenas entre idiomas.
4. Usar Gemini para imagem (imagem é só Flow — §58.2 do manual).

**Trava automática:** `scripts/check_imagens_compartilhadas.py`.
Depois da fase de imagens o `gerar_capitulo_trilinguo.py` grava
`artifacts/images_manifest.json` (nome + sha1 de cada imagem) com `--update`;
**antes de cada render**, confere o manifesto. Se alguma imagem aparecer,
sumir ou mudar entre idiomas, o capítulo **aborta** — porque as 3 versões têm
que sair da mesma pasta.

```powershell
python scripts/check_imagens_compartilhadas.py --slug <slug>          # confere
python scripts/check_imagens_compartilhadas.py --slug <slug> --update # apos gerar
```

**Trava de idioma:** `scripts/check_texto_idioma.py` falha se
`script_en.json`/`script_es.json` tiver o título em PT dentro da narração ou
uma recusa do Gemini ("sou apenas um modelo de linguagem"). O s0 é montado
do título traduzido (não passa pelo Gemini) justamente para não vazar PT.
Antes de publicar, rodar também com `--strict` (badge "Frida e Luna" no
overlay EN/ES bloqueia).

Se uma imagem estiver errada: corrija **uma vez**, regenere **só ela** e
re-renderize os três idiomas (não gere por idioma).

---

## 5.10. MP4 só vale se for mais novo que as imagens (regra dura)

O `gerar_capitulo_trilinguo.py` **não reaproveita** um `.mp4` só porque o
arquivo existe. Ele compara a data do vídeo com a data das dependências
daquele idioma:

- todas as imagens de `assets/images/gemini/scenes/`
- `artifacts/scenes.json`, `artifacts/image_prompts.json`
- `artifacts/script_<lang>.json`, `artifacts/narration_timing_<lang>.json`
- `assets/audio/narration/<lang>/`, `scenes/<lang>/`, `assets/subtitles/<lang>/`

Se qualquer dependência for mais nova, o vídeo é considerado **desatualizado**
e é **re-renderizado** (com o log `existe mas esta DESATUALIZADO ...`).

Isso já causou problema real: as 27 imagens do Chihuahua foram refeitas, mas os
MP4 antigos (com a figura repetida) foram reaproveitados e teriam sido
publicados de novo. **Nunca** "consertar" isso apagando a checagem: se o vídeo
re-renderizou sem necessidade, o certo é investigar por que a dependência ficou
mais nova.

Regra prática: mudou imagem, roteiro, overlay, narração ou legenda → os três
MP4 daquele projeto precisam ser refeitos antes de publicar.

---

## 5.11. Tema de vídeo novo: a fila `scripts/topics.txt` (regra dura)

Todo vídeo novo (inclusive os de tópico randomizado) sai da fila oficial
`scripts/topics.txt`. O arquivo tem três partes:

- fila comum: uma linha por tema, na ordem;
- `# ----- USADOS -----`: tema | slug | data dos vídeos já feitos (não sorteia);
- `# ----- datas especiais -----`: `@MM-DD`, só saem na data.

Fluxo obrigatório antes de gerar um vídeo:

1. **Ler** `scripts/topics.txt` (a lista é a memória dos temas do canal).
2. **Sortear** um tema ainda não usado: `python scripts/select_topic.py`.
3. **Conferir duplicidade**:
   `python scripts/check_topico_novo.py --tema "tema escolhido"`.
   Se parecer com qualquer linha (inclusive usados), escolha outro.
4. Ao terminar o vídeo, **registrar o usado** no próprio arquivo, em
   `# ----- USADOS -----`, no formato `tema | slug | AAAA-MM-DD`.

Nunca: apagar a fila, reformatar a lista inteira para `- tema`, repetir tema
já publicado, ou usar tema que não está na lista sem acrescentá-lo antes.

O hook `.githooks/pre-commit` roda `scripts/check_topico_novo.py` e bloqueia
commit com fila ausente/vazia ou sem nenhum tema livre.

---

## 6. Resumo em 30 segundos

1. Ler `CONTRATO.md` + `MANUAL_GRAFOS.md` + docstring do `pipeline.py`.
2. Criar branch com nome curto e óbvio.
3. Fazer a mudança **e** atualizar o `MANUAL_GRAFOS.md` no mesmo commit.
4. Rodar os checks (`check_manual`, `check_prompt_repeticao`,
   `check_imagens_repetidas`, `check_texto_idioma`, `check_topico_novo`).
5. Commit + push da branch.

**O manual é a memória do produto. Se não está no manual, não existe.**

**Imagem: uma cena diferente por pausa.** A referência é só o design das
personagens — nunca a cena (§5.8). Vídeo com a mesma figura repetida não se
renderiza nem se publica.
