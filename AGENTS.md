# AGENTS.md — Videomaker

## 🛑 REGRA DE OURO DO AGENTE (2026-11-20) — NAO QUEBRAR

**Toda sessão COMEÇA com:**
```powershell
python scripts/agent_briefing.py --slug <slug>
```
Ele imprime as fórmulas prontas e roda as travas. **Nunca reimplementar o que
já existe** (`publish_multilang.py`, `gerar_capitulo_trilinguo.py`,
`check_texto_idioma.py`, `check_imagens_compartilhadas.py`,
`gen_narration_voicecraft.py`). Se algo deu errado antes, procure no
`git log --all --oneline --grep="..." -i` — a correção já foi feita.

Antes de PUBLICAR, o Hook `antes_publicar` bloqueia se faltar: idioma do
overlay, credencial do canal, `kids=False`, thumbnail no idioma, ou folha de
referência entre as imagens. **Não contorne o Hook.**

**Leia `CONTRATO.md` e `MANUAL_GRAFOS.md` ANTES de fazer qualquer coisa.**
O manual é a fonte de verdade do produto: o que já está feito, como está e por
quê. Não refaça e não desfaça o que já está resolvido.

**🧠 GRAFO (memória viva) — leia ANTES de qualquer pergunta sobre o sistema.**
O knowledge graph em `graphify-out/` é a fonte comprimida do que já foi feito.
Para não gastar token lendo arquivos gigantes, rode primeiro:

```powershell
graphify query "sua pergunta" --budget 1500
```

Exemplos: `graphify query "como gerar imagens com personagens consistentes"`,
`graphify query "qual a regra de duracao do video"`.
O grafo é atualizado automaticamente a cada commit pelo hook `post-commit`
(`graphify hook install`). Se você alterou um manual e o grafo parecer velho,
rode `graphify . --update` (incremental, barato) antes de sair.

| Arquivo | Ler quando |
|---------|-----------|
| `graphify-out/GRAPH_REPORT.md` | **primeiro** — resumo do grafo (comunidades, nós-de-deus, decisões) |
| `graphify query "..."` | para qualquer pergunta específica (barato em token) |
| `CONTRATO.md` | sempre (regras de trabalho) — ver §5.8 antes de mexer em imagem |
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
4. **`scene_density.scene_mode` continua `two`?** (Antes de 2026-11-15: sim, era
   `two`. Desde **2026-11-15** o default virou **`beats`** — 1 imagem nova por beat
   de narração, prompts por beat com CENA + REGRA ANTI-REPETIÇÃO. Não trocar sem
   prova. A trava `check_prompt_repeticao.py` aceita `two` **ou** `beats`.)
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
9. **Google Flow via `flow_fetch.py`:** nunca usar `--ref-image` (file chooser
   do Chrome trava no modo CDP/headless). O `flow_fetch` já injeta os
   personagens Frida e Luna via prompt (`_enforce_characters`). Se a UI do Flow
   mudou (toggle de modo Imagem sumiu), rode `python scripts/flow_fetch.py
   --setup` para reaprender e salvar o estado em `.flow_learned_state.json`.
   O Flow gera imagem por padrão — não precisa selecionar "Modo Imagem".
10. **Vídeo NÃO é conteúdo para crianças.** Todo vídeo publicado nos 3 canais
    (PT/EN/ES) deve ser marcado como `selfDeclaredMadeForKids=false`. O upload
    padrão já usa `--nao-kids`; se precisar corrigir vídeos antigos, rodar
    `python scripts/atualizar_kids.py <pt|en|es>` para marcar todos de uma vez
    ou `python scripts/youtube_metadados.py --lang <lang> --video-id <ID>
    --proj <caminho> --atualizar --nao-kids` para um vídeo individual.
11. **Duração mínima obrigatória — REGRA DE OURO.** O vídeo e o áudio devem ter **mais de 10 minutos**, preferencialmente **15 minutos**. O áudio final (`assets/audio/final_mix.m4a`) deve durar entre 10 e 15 minutos. O roteiro core deve ter entre **1 500 e 2 000 palavras**. Se não atingir, o vídeo está **reprovado** e deve ser refeito.

Se qualquer resposta for "sim, estou fazendo isso" → **pare e conserte antes**.
Detalhes: `CONTRATO.md` §5.8 e `MANUAL_GRAFOS.md` §58.6.

**REGRA OBRIGATÓRIA — LEIA O MANUAL GRAFOS.md:**
Antes de tocar em qualquer coisa (código, prompt, imagem, cena, `scene_mode`, render,
narração, trilha, upload), leia **`MANUAL_GRAFOS.md`** inteiro ou pelo menos a seção
relevante. Ele é a memória do produto: contém o que já foi feito, como está e por quê.
Se algo está documentado no manual, **já foi feito** — não refaça. Se está documentado,
**não está quebrado** — não desfaça.
Detalhes: `MANUAL_GRAFOS.md` §0 e §38.

## Ambiente (hardcoded, não adivinhe)

- Python: `C:\OpenMontage\.venv\Scripts\python.exe` (sempre use este caminho)
- Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- ffmpeg: `C:\videomaker\ffmpeg\bin\ffmpeg.exe`
- Chrome CDP: porta `18800` (perfil `C:\videomaker\.chrome-gemini-profile\`)
- Só um render por vez (ffmpeg não é thread-safe aqui)
- Um render completo leva **6–10 minutos** por idioma. Rodar em background (`Start-Process` ou `.ps1` script) ou com timeout alto.

## PowerShell (gotchas do Windows)

- `&&` **não funciona** no PowerShell. Use `;` ou quebre em linhas separadas.
- `tail` **não existe**. Use `Get-Content <arquivo> -Tail N` ou `Select-Object -Last N`.
- `grep` **não existe**. Use `Select-String -Pattern "<texto>"`.
- `head` **não existe**. Use `Select-Object -First N`.
- **`Start-Process -ArgumentList` divide strings com espaços** em múltiplos argumentos.
  Prompts com espaços ou acentos quebram. Usar `.ps1` ou `.bat` com `chcp 65001` e
  `PYTHONIOENCODING=utf-8`:
  ```powershell
  # NÃO: Start-Process python -ArgumentList "scripts/foo.py", "--prompt", "O campeonato de cães..."
  # SIM: criar run_x.ps1 com o comando e Start-Process powershell -ArgumentList "-File", "run_x.ps1"
  ```
- Para rodar em background: `Start-Process -FilePath "<exe>" -ArgumentList @("<arg1>", "<arg2>") -Wait`
- Para matar processos Python travados: `Get-Process | Where-Object Name -like 'python*' | Stop-Process -Force`

## Fluxo de trabalho (obrigatório)

1. **Branch antes de mexer**: `git checkout -b feature/nome-curto`.
2. **O `MANUAL_GRAFOS.md` vai no mesmo commit da mudança.** Se mudou fluxo,
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
# Python sempre com caminho absoluto
$py = "C:\OpenMontage\.venv\Scripts\python.exe"

# Pipeline completo (3 idiomas)
& $py scripts\gerar_capitulo_trilinguo.py --prompt "<tema>" --slug <slug>

# Só um idioma
& $py scripts\gerar_capitulo_trilinguo.py --prompt "<tema>" --slug <slug> --only-lang es

# Upload por idioma
& $py scripts\upload_por_idioma.py pt --projects-dir "C:\videomaker\projects" --slug <slug> --force

# Corrigir madeForKids (todos os vídeos do canal)
& $py scripts\atualizar_kids.py pt   # ou en, es

# Listar canal
& $py scripts\listar_canal.py --lang pt

# Checks
& $py scripts\check_manual.py
& $py scripts\check_prompt_repeticao.py
& $py scripts\check_imagens_repetidas.py
& $py scripts\check_texto_idioma.py --strict
& $py scripts\check_topico_novo.py --tema "..."

# Tópico novo
& $py scripts\select_topic.py
& $py scripts\check_topico_novo.py --tema "<tema escolhido>"

# Flow (Google Flow para imagens)
& $py scripts\flow_fetch.py --setup   # interativo: configurar no navegador, depois Enter
& $py scripts\flow_fetch.py --check   # ver se Chrome/Flow estão respondendo

# End screen (tela final) — NÃO existe na API do YouTube v3 (descontinuado).
# Fazer manualmente no YouTube Studio: Conteúdo → Vídeo → Editor de vídeo → Tela final
```

## Lições operacionais desta sessão (2026-11-15)

- **Arquivo `.bat` com acentos**: gravar como **UTF-8 com BOM** ou usar `\u00e3` escapado no Python e gravar em binário (`wb`). O PowerShell corrompe acentos ao fazer `Out-File` / `Set-Content`.
- **Flow trava em imagem específica**: se `desenvolvimento_5_scene` (ou qualquer prompt) travar no loop do `flow_fetch`, gerar a imagem isolada via `flow_fetch.py --only <nome> --wait 180` costuma resolver. Copiar o resultado para `assets/images/gemini/scenes/` desbloqueia o pipeline.
- **Pipeline pula arquivos existentes**: `gerar_capitulo_trilinguo.py` reutiliza script, cenas, imagens, narração se já existirem. Para re-gerar, apagar o artefato alvo.
- **Chrome CDP deve estar ativo**: `Start-Process chrome.exe --remote-debugging-port=18800 --user-data-dir=C:\videomaker\.chrome-gemini-profile`. Confirmar com `python flow_fetch.py --check`.
- **Render em background**: usar `.ps1` com `Start-Process powershell -File run_x.ps1` ou `cmd /c run_x.bat` para evitar timeout do shell wrapper.
- **Tema usado**: sempre registrar em `scripts/topics.txt` na seção `# ----- USADOS -----` no formato `tema | slug | YYYY-MM-DD` e remover da lista livre.
- **`scene_mode = "beats"` (default desde 2026-11-15)**: gera **1 imagem por beat** de narração (mín. 7 / máx. 16 palavras por beat); beats > 2 usam sufixo `_scene_c`, `_scene_d`... no nome. `two` continua por flag. Travas de prompt/imagem passam a aceitar `beats` (com prompts por beat regenerados e validados).
- **Local de gravação do Flow**: `flow_fetch.py` grava imagens em `<proj>/public/assets/images`; o canônico da pipeline (checks, preprocess, build) é `<proj>/assets/images/gemini/scenes` — copiar o que foi gerado para lá antes de renderizar.

## Hooks (instalar uma vez por clone)

```powershell
python scripts/install_hooks.py
```

Ativa `.githooks/pre-commit` e `.githooks/pre-push`: sintaxe Python, trava de
prompt, trava de imagem repetida e `check_manual.py`. Não desative.

Detalhes: `CONTRATO.md`.

## Estado que NÃO sobe para o git (ignorado)

- `projects/` (vídeos, áudios, imagens geradas)
- `scripts/.publish_history_idioma.json` (controle de uploads)
- `scripts/.publish_history.json`
- `.flow_learned_state.json` (estado do setup do Flow)
- `.chrome-gemini-profile/` (sessão do Chrome)
- `*.log`, `*.mp4`, `*.jpg`, `*.png`, `*.wav`, `*.m4a`
- `ffmpeg/`, `hyperframes-workspace/`, `banco de imagens/`, `banco de músicas/`
- `scripts/client_secret*.json`, `scripts/*token*.json`, `scripts/config.json`





## Regras de Efeitos Sonoros (SFX) e Áudio (2026-11-20)



- Sempre utilize o módulo `gerenciador_efeitos_sonoros.py`

  (`obter_efeito_sonoro`) para obter qualquer efeito sonoro do vídeo.

  **Nunca crie caminhos de áudio fictícios.** Sons locais só são aceitos se o

  arquivo existir (`origem="local"` valida antes de devolver o caminho).

- Quando usar `origem="earshot"`: para todos os sons de ritmo, interface,

  transições de cena, cortes secos, impactos, subidas de tensão e alertas

  (`whoosh_fast/crisp`, `ui_pop`, `cut_hit`, `riser`, `knock`, `shutter`,

  `reverse_swell`). Antes de escolher um ID do Earshot, rode

  `earshot sfx list` se tiver dúvida sobre o nome exato.

- Quando usar `origem="freesound"`: para sons realistas e específicos de

  ambiente, objetos, máquinas, animais, clima ou ações complexas

  (ex: "forest rain", "dog bark", "explosion debris", "typewriter"). Use

  sempre termos de busca curtos em inglês (2 a 3 palavras). Requer

  `FREESOUND_API_KEY` no `.env` (se ausente, o módulo avisa e não inventa som).

- Mixagem no FFmpeg: sempre normalize e atenue o volume dos efeitos sonoros

  (ex: `-filter:a "volume=0.35"`) ao misturar com a faixa de narração

  principal para não encobrir a voz. Na sonoplastia atual isso equivale ao

  ducking com earshot (efeitos caem para 55% durante a fala).

- No Earshot, use sempre o ID completo no formato familia/variante

  (ex: `whoosh_fast/crisp`, `swipe/paper`, `swish/bright`) e só passe

  `--pitch` ou `--dur` se aparecerem na coluna `knobs` de `earshot sfx list`.

- Anti-laser: `osso_assobio` (apito puro 1454 Hz), `zap`, `glitch`, `zing`,

  `whistle`, `logo_sting`, `downlifter` e `sub_drop` continuam proibidos.

  `riser` é permitido apenas para subida de tensão, com ganho baixo e ducking.





## AUDITORIA VISUAL E DE IDIOMA OBRIGATORIA (2026-11-20)



Motivo: o usuario teve que apontar erros que a auditoria antiga nao pegou.

Causa: `check_personagens_imagens.py` era STUB (`auditar()` = NotImplementedError)

e `make_contact_sheet.py` apontava para OUTRO projeto. Nada rodava no Hook.



Ferramentas reais (rodar ANTES de renderizar/publicar):

  python scripts/auditoria_visual.py --slug <slug> --lang <lang>

  # abre as 4 folhas de contato em conferencia/auditoria_visual/ e OLHA

  python scripts/auditoria_visual.py --slug <slug> --lang <lang> --revisar

  python scripts/auditoria_idioma.py --slug <slug> --lang <lang>



O Hook (`antes_render`, `antes_publicar`) BLOQUEIA se faltar:

  - auditoria_visual_<lang>.json com status PASS e revisado_por_agente=true

  - auditoria_idioma_<lang>.json com status PASS (Whisper detecta o idioma falado)

  - roteiro <lang> sem marcadores de outro idioma

O `publish_multilang.py` tambem dispara o Hook antes de cada upload.

Somente apos aprovacao explicita do usuario (`pode publicar`) o upload acontece.


## Gerenciador de Efeitos Sonoros — `gerenciador_efeitos_sonoros.py` (2026-11-20)

Ponto único para obter QUALQUER efeito sonoro no pipeline. Nunca monte caminhos
de áudio manualmente.

```python
from gerenciador_efeitos_sonoros import obter_efeito_sonoro

# Earshot (procedural, 252 sons): ritmo, UI, transições, cortes, impactos, tensão, alertas
som = obter_efeito_sonoro("whoosh_fast/crisp", origem="earshot", duracao=0.6)

# Freesound (realistas, CC0): ambiente, objetos, máquinas, animais, clima
# Requer FREESOUND_API_KEY no .env
som = obter_efeito_sonoro("forest rain", origem="freesound", max_duracao=5.0)

# Local (sons domésticos reais): só aceita arquivo existente
som = obter_efeito_sonoro("espirro.wav", origem="local")
```

### Regras obrigatórias (validados no Hook `antes_publicar`)

1. **Ponto único**: `obter_efeito_sonoro` é a ÚNICA forma de obter SFX.
   - `sonoplastia_por_idioma.py` JÁ USA o gerenciador (não use `bank.render()` direto).
   - `gerar_sonoplastia.py` (antigo) é LEGACY — não use.

2. **Earshot** (`origem="earshot"`): sons de ritmo, UI, transições, cortes, impactos, tensão, alertas.
   - IDs: `familia/variante` exato do `earshot sfx list` (ex: `whoosh_fast/crisp`, `swipe/paper`, `swish/bright`, `riser/air`).
   - Só passe `--pitch` ou `--dur` se a coluna `knobs` do `earshot sfx list` mostrar.

3. **Freesound** (`origem="freesound"`): sons realistas de ambiente, objetos, máquinas, animais, clima, ações complexas.
   - Busca em inglês, 2-3 palavras: `"forest rain"`, `"dog bark"`, `"explosion debris"`, `"typewriter"`.
   - Requer `FREESOUND_API_KEY` no `.env` (grátis em freesound.org). Se ausente, o módulo avisa e NÃO inventa som.

4. **Local** (`origem="local"`): sons domésticos reais em `assets/audio/sons/`.
   - Só aceita arquivo que EXISTA (`buscar_som_local` valida antes de devolver caminho).

5. **Mixagem**: SEMPRE atenue efeitos (`volume=0.35` no FFmpeg ou ducking earshot 55% durante fala).
   - Na sonoplastia atual: ducking com earshot (efeitos caem para 55% durante fala).

6. **IDs Earshot**: SEMPRE `familia/variante` (ex: `whoosh_fast/crisp`, `swipe/paper`).
   - Só passe `--pitch`/`--dur` se a coluna `knobs` do `earshot sfx list` permitir.

6. **Anti-laser** (2026-11-20): Tons puros/agudos proibidos.
   - `SONS_PROIBIDOS` em `sonoplastia_por_idioma.py`: `osso_assobio` (apito 1454Hz), `zap`, `glitch`, `zing`, `whistle`, `logo_sting`, `pro_logo_sting`, `downlifter`, `sub_drop`, `glitch/chirp`.
   - `riser` permitido APENAS para subida de tensão, com ganho baixo + ducking.
   - Filtro automático `som_eh_laser()` bloqueia tons puros/agudos (flatness > -18 dB E centroide > 700 Hz).

### Como adicionar novos sons domésticos

1. Coloque o `.wav` em `assets/audio/sons/` do projeto.
2. Adicione em `SONS_LOCAIS` no `render_cue()` de `sonoplastia_por_idioma.py`.
3. Use `origem="local"` no dicionário `PALAVRAS`.
