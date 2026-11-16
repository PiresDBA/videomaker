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
