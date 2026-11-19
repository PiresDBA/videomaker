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

## 5.7.1. Vídeo NÃO é conteúdo para crianças (regra dura — selfDeclaredMadeForKids=false)

Todo vídeo publicado nos 3 canais (PT/EN/ES) deve ser marcado como **não feito
para crianças** (`selfDeclaredMadeForKids = false`) no status do YouTube.

- Nunca publicar com `made_for_kids=true` ou `selfDeclaredMadeForKids=true`.
- O upload padrão (`scripts/upload_por_idioma.py`) já usa `--made-for-kids`
  como default `True`; para desativar, usar `--nao-kids` ou chamar
  `scripts/atualizar_kids.py <lang>` após o upload.
- Se o vídeo já foi publicado com kids=true, rodar:
  `python scripts/youtube_metadados.py --lang <pt|en|es> --video-id <ID> --proj <caminho_projeto> --atualizar --nao-kids`
  ou, para todos os vídeos do canal de uma vez:
  `python scripts/atualizar_kids.py <pt|en|es>`
- Verificar com `python scripts/listar_canal.py --lang <lang>` que nenhum
  vídeo está marcado como kids.

Regra aplicada a todos os 149 vídeos publicados até 2026-11-15
(PT=84, EN=54, ES=11) via `scripts/atualizar_kids.py`.

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

## 5.12. Duração mínima do vídeo e áudio — REGRA DE OURO (regra dura)

- Vídeo e áudio devem ter **mais de 10 minutos**, preferencialmente **15 minutos**.
- O áudio final (`assets/audio/final_mix.m4a`) deve durar entre **10 e 15 minutos**.
- O roteiro core (seções s1 até antes de s_final) deve ter entre **1 500 e 2 000 palavras**.
- Se a narração/áudio final for inferior a 10 minutos ou o roteiro core ficar fora de 1 500-2 000 palavras, o vídeo está **reprovado** e deve ser refeito integralmente (roteiro mais longo, mais beats, ou re-geração).
- Essa regra vale para PT/EN/ES; a geração de imagens é única, mas a duração do áudio narrado é verificada por idioma.
- O pipeline deve validar duração após `final_mix` e abortar publicação caso a regra seja violada.

## 5.15. Variedade visual: colagens (1/2/3/4 painéis) e imagens individuais

Para o visual não ficar "chapado", o gerador de imagens alterna entre:

- **colagem de 3 cenas** (tríptico, 3 painéis lado a lado),
- **colagem de 2 cenas** (dupla),
- **colagem de 4 cenas** (4 painéis),
- **imagem individual** (uma cena por arquivo).

A **orientação também varia entre beats**: às vezes os painéis ficam lado a lado
(divisão horizontal da tela), às vezes empilhados (divisão vertical da tela),
como histórias em quadrinho. O canal validou esse estilo em 2026-11-17; detalhes
e estado da implementação em `MANUAL_GRAFOS.md` §60.

Regras:

- A colagem é pedida no prompt e depois **fatiada** pelo script
  (`flow_agent_batch.py`, `dividir_colagem`) em um `.jpg` por cena, mantendo a
  ordem (painel 1 = cena 1, painel 2 = cena 2...).
- Mesmo quando se pede "imagens separadas", o Flow pode entregar uma colagem;
  o divisor detecta pela proporção e fatia da mesma forma.
- Todo painel precisa manter **os mesmos personagens nomeados** (Frida, Luna,
  Pipoca, Penélope) e a Bíblia de Continuidade (§5.13).
- O tríptico foi validado visualmente e agrada o canal — usar com frequência.
- Nunca repetir a mesma divisão (quantidade + orientação) em beats seguidos.

## 5.14. Narração com emoção (regra dura)

A voz do canal precisa soar **alegre, empolgada e carinhosa**, nunca robótica:

- PT: `pt-BR-ThalitaNeural`, `rate +6%`, `pitch +12Hz`.
- EN: `en-US-AriaNeural`, `rate +4%`, `pitch +8Hz`.
- ES: `es-ES-ElviraNeural`, `rate +4%`, `pitch +8Hz`.
- O `gerar_capitulo_trilinguo.py` (`garantir_narracao`) deve passar esses valores;
  **nunca** `--rate +0% / --pitch +0Hz`.
- A emoção também vem do texto: frases curtas, "..." e "Hahaha!" escritos no
  roteiro (o narrador lê em voz alta). SSML/style é evitado porque o Edge-TTS
  lê as tags como jargão falado.
- Ajustar precisa manter a REGRA DE OURO: áudio final entre 10 e 15 min.

## 5.13. Auditoria de personagens nas imagens (regra dura)

Depois de **toda** geração de imagens (individual ou em lote/Agente), é obrigatório
auditar as imagens antes de renderizar:

- Todo cachorro em cena precisa ser um personagem **nomeado e fixo**:
  - **Frida** = buldogue inglesa fawn, grande, compacta, com colar de pérolas.
  - **Luna** = dachshund/salsicha marrom-chocolate, corpo comprido, pernas curtas, coleira dourada.
  - Qualquer personagem novo (Pipoca = chihuahua amarelinho, Penélope = poodle branca, etc.)
    deve ser **criado no Google Flow** com nome e características fixas e citado pelo nome no prompt.
- O Flow **não mantém personagens sozinho**, mesmo com "IDENTIDADE FIXA" no prompt:
  ele troca a raça (Frida vira pug/poodle, Luna vira labrador) quando o prompt é longo
  ou o lote é grande. A auditoria visual detecta isso.
- Imagem com cachorro que não é um personagem nomeado, sem humano (o canal não tem
  humanos em cena), ou com personagem trocado → **vai para loop de re-geração**.
- Regras de prompt para imagem (tanto individual quanto lote):
  1. usar os personagens **salvos no Flow pelo nome** (Frida, Luna, Pipoca...);
  2. se o personagem não existir, criar no Flow primeiro com nome + raça + cor + tamanho;
  3. repetir a identidade no prompt mesmo assim;
  4. lotes pequenos (≤4 imagens) para reduzir a troca de personagem;
  5. auditoria visual obrigatória após gerar.

---

## 5.16. Grafo de conhecimento é a memória viva (regra dura)

- O knowledge graph em `graphify-out/` (gerado pelo graphify) é a **fonte
  comprimida** de tudo que já foi decidido e feito no sistema.
- **Todo agente que entrar aqui deve começar com `graphify query "<pergunta>" --budget 1500`**
  em vez de ler arquivos gigantes — economiza token e não perde contexto.
- **Sempre que qualquer manual mudar** (`AGENTS.md`, `CONTRATO.md`,
  `MANUAL_GRAFOS.md`) é obrigatório atualizar o grafo **no mesmo commit**:
  `graphify . --update` (incremental/barato) — ou o hook `post-commit` faz isso.
- O hook `graphify hook install` roda após cada `git commit` e mantém
  `graph.json` / `GRAPH_REPORT.md` atualizados. Verificar com
  `graphify hook status`.
- Se um commit mudou manual e o grafo ficou velho, rode `graphify . --update`
  manualmente antes do push. Grafo desatualizado = próximo agente repete trabalho.

## 5.17. Prompt de imagem: curto e em inglês (regra dura)

- O Flow rejeita prompts longos em português (~3.000+ chars) com "Falha: esta
  geração talvez viole nossas políticas" (sem cobrança). Não é falta de crédito.
- Usar prompts **curtos (~400 chars) em inglês**: estilo Pixar 3D + identidade de
  Frida/Luna pelo nome + a cena em 1 linha + proibições básicas.
- `scripts/encurtar_prompts.py` gera `image_prompts_short.json`; o batch usa esse
  arquivo. Com prompt curto o Flow gera na 1ª tentativa e mantém os personagens.
- Auditoria visual (§5.13) continua obrigatória: verificar personagem e cenário.

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





## REGRA FLOW_GUARD (2026-11-19) - IMAGENS SEMPRE NO GOOGLE FLOW



> Toda geracao de imagem DEVE usar o Google Flow. A degradacao e progressiva:

> lotes de 15, 12, 10, 8, 4, 2 e, por ultimo, 1 por 1 no PROPRIO Flow,

> insistindo 10 VEZES no tamanho 1. Somente apos esgotar TODAS essas tentativas

> no Flow e permitido cair no Gemini, como ULTIMO recurso.

> NUNCA cair no Gemini logo na primeira falha. O `flow_guard` no

> `flow_agent_batch.py` garante isso. Seletor de editor com acento corrompido

> no perfil aprendido pode fazer `validate_flow_ready` retornar False e

> causar fallback indevido — validar com `python scripts/flow_fetch.py --check`.





## REGRA PROMPTS_VIDEOS (2026-11-19) - VIDEOS EM PARALELO



> Logo apos gerar o roteiro (fase script), o pipeline DEVE gerar o arquivo

> PROMPTS_VIDEOS.md na raiz do projeto, com os 5 prompts dos videos (intro +

> 3 meio + final). O usuario gera esses videos manualmente no Google Flow

> ENQUANTO o pipeline continua gerando as fotos. Estilo OBRIGATORIO nos

> prompts: cinematografico 3D Disney/Pixar, 8 SEGUNDOS, @Frida e @Luna

> (arro sem colchetes), referencia anexada. Sonoplastia sempre incluida

> (gerada pela narracao). Se o Flow automatico falhar apos todas as

> tentativas, este e o fallback oficial para os videos.





## REGRA HULK - GUARDA DO CONTRATO (2026-11-19)



> `scripts/hulk_validator.py` E O GUARDA. Roda automaticamente ANTES de

> publicar (phase_youtube) e pode ser chamado a qualquer momento:

> `python scripts/hulk_validator.py --slug <slug>`.

> Se alguma regra abaixo foi quebrada, ELE AVISA e BLOQUEIA.



### ERROS QUE ACONTECERAM (NUNCA REPETIR)



1. **Imagens duplicadas** (mesmo hash em cenas diferentes) -> 10 imagens

   desperdicadas e 15h de retrabalho. CORRECAO: checar duplicatas por hash

   antes de renderizar; apagar e regerar as segundas ocorrencias.

2. **Detector de duplicata agressivo** (media<2.0) descartava cenas parecidas

   com a referencia e travava a geracao. CORRECAO: tolerancia 0.5 (so copia

   exata). Foram DOIS detectores (`_imagem_repetida` E `_bytes_igual_ref`) —

   os DOIS corrigidos.

3. **Seletor do Flow com acento corrompido** (`vocǦ`) fazia

   `validate_flow_ready` retornar False -> pipeline cair no Gemini na hora,

   sem tentar o Flow. CORRECAO: seletores genericos no perfil aprendido.

4. **Gemini antes de esgotar o Flow** -> inconsistentia dos personagens.

   CORRECAO: FLOW_GUARD (15->12->10->8->4->2->1 no Flow, 10x no tamanho 1,

   so depois Gemini).

5. **Rate limit do Flow** ("solicitacoes muito rapido") -> geracao reiniciava.

   CORRECAO: pausa padrao 120s e estabilizacao 120s apos imagens.

6. **Timeout de 28 min** por lote travava sem mensagem de erro. CORRECAO:

   teto de 5 min (300s) por lote e degradação de tamanho.

7. **`@[Frida]` com colchetes** -> Flow nao reconhecia. CORRECAO: sintaxe

   correta e `@Frida` / `@Luna` (arro, sem colchetes), em prompts e scenes.

8. **`_cena_do_prompt` so extraia a 1a linha** e perdia as referencias dos

   personagens. CORRECAO: funcao sempre injeta @Frida/@Luna.

9. **Modo Agente do Flow trocava personagens / painel lateral travava envio**.

   CORRECAO: fechar painel, desligar agente no batch, usar ref-image.

10. **Videos das maos do usuario inconsistentes** -> fallback oficial:

    PROMPTS_VIDEOS.md gerado apos o roteiro, estilo cinematografico 3D

    Disney/Pixar + @Frida/@Luna + 8 SEGUNDOS, usuario gera em paralelo.

11. **Slug truncado pelo PowerShell** com acento no prompt -> use `resume

    --slug <slug>` (sem prompt) para retomar projetos existentes.

12. **Criar pipeline/config paralelo** -> ERRADO. Orquestrador UNICO e

    `scripts/pipeline.py`; regras sao ARGUMENTOS dele (`--flow-agent`,

    `--batch-size`, `--clipes-meio`, `--sonoplastia`, `--efeitos-fundo`,

    `--ref-personagem`).



### SONOPLASTIA E OBRIGATORIA



Gerada APENAS ouvindo o arquivo de narracao (faster-whisper), som na palavra

exata, efeitos de fundo (estrelinhas/folhas/abelhas) e blur/foco pulsante.

NUNCA pular. Flag `--sonoplastia on` e padrao.





## REGRA RETRY RECUSA - BOTAO "TENTAR DE NOVO" (2026-11-19)



> Quando o Flow mostrar "Falha - Esta geracao talvez viole nossas politicas",

> o botao CERTO e "Tentar de novo" (icone refresh 🔄) dentro do card da falha.

> O `flow_fetch.retry_refused_image()` clica ate 10 vezes, esperando 2 minutos

> entre cada tentativa, ANTES de desistir. NUNCA usar "Reutilizar comando"

> (undo/redo) - estava errado e nao resolvia.

> Se aparecer "solicitacoes muito rapido", aumentar a pausa (padrao 120s).

> Corrigido em `fa05f0a`.


## COMPILACAO FINAL - VIDEOMAKER_PROJ (2026-11-19)

> `build_composition.py` le `artifacts/video_clips.json` da variavel de ambiente
> `VIDEOMAKER_PROJ` (NAO do `--proj`). Sem ela os 5 clipes manuais somem da
> composicao e o video sai "pelado". `pipeline.phase_compose` agora seta a
> variavel automaticamente (commit d3ba51e).
>
> REGRAS DA COMPILACAO FINAL:
> 1. `pre_final` = clipe de pata/confete (final_subscribe2.mp4) no instante
>    em que a narracao fala "obrigado por assistir".
> 2. `outro` = final_subscribe.mp4 no instante em que fala "like/se inscreva".
> 3. Renderizar SEM a fase `mix` (`--only compose,preprocess,render`) para nao
>    sobrescrever `final_mix.m4a` com sonoplastia.
> 4. Mix final DEVE ser igual a `final_mix_sonoplastia_<lang>.m4a`.
> 5. Composicao final DEVE ter >=5 videos, particulas > 0 e focus-pulse > 0.
> 6. Hulk valida tudo isso (regras 10 e 11) antes de publicar.
