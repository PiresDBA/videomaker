# Guia de reprodução — Pipeline de vídeo Videomaker v3

Este documento ensina a **gerar um vídeo do zero a partir de um prompt**, usando os scripts locais do projeto. Sem chaves de API: a narração é local (Edge-TTS) e os pontos de IA (roteiro, imagens, música) usam scraping do Gemini web pelo Chrome.

Diretório raiz: `C:\videomaker`.
Cada prompt vira um **projeto independente** em `projects/<slug>/` — a entrega final nunca colide com outro projeto.

> **Overlays:** por padrão as cenas têm apenas a caixa de texto à esquerda. Os
> antigos "chips" de 4 palavras à direita ficam desativados (só com `--chips`).
> Ver `MANUAL_GRAFOS.md` para os grafos do pipeline e os comandos de regeneração/render.

Última entrega: `projects/video-engracado-sobre-buldogue-ingles-co/output/video-engracado-sobre-buldogue-ingles-co.mp4` — 283,9s, 1920x1080 @30fps, H.264 + AAC, −14,1 LUFS / −1,7 dBTP.

---

## 1. Visão geral — 10 fases com checkpoints

O orquestrador `scripts/pipeline.py` roda as fases na ordem abaixo. Cada fase gravada guarda um checkpoint em `projects/<slug>/project.json`; execuções seguintes **pulam** as fases completas (não repete Gemini nem render desnecessariamente).

| # | Fase | Script | IA? | Gera (em `projects/<slug>/`) |
|---|------|--------|-----|------------------------------|
| 1 | `script` | `generate_script_from_prompt.py` | Gemini web | `artifacts/script.json` |
| 2 | `scenes` | `generate_scenes_and_prompts.py` + `generate_scene_htmls.py` | local | `artifacts/image_prompts.json`, `artifacts/scenes.json`, `scripts/scenes/s*.html` (injetados na composição) |
| 3 | `images` | `fetch_images.py --single` (uma por vez) | Gemini web | `assets/images/gemini/scenes/*.jpg` |
| 4 | `music` | `fetch_music_gemini.py` (ou procedural) | Gemini web | `assets/audio/gemini/bgm_gemini.wav` |
| 5 | `narration` | `gen_narration_edge.py` | local (Edge-TTS) | `assets/audio/narration/s*.mp3` + `artifacts/narration_timing.json` |
| 6 | `timeline` | `build_timeline.py` | local | `narration_full.wav` + `artifacts/timeline.json` |
| 7 | `mix` | `mix_audio.py` | local | `assets/audio/final_mix.m4a` |
| 8 | `compose` | `build_composition.py` | local | `composition.html` |
| 9 | `preprocess` | `preprocess_images.py` | local | imagens 1920x1080 no projeto HyperFrames |
| 10 | `render` | `scripts/render.ps1` + `verify_output.py` | local | `output/<slug>.mp4` |

Cada fase imprime `== FASE <nome>: iniciando` no stdout. Quando `images` está no plano
junto com `music`, a música roda **antes** das imagens (sequencial) para não disputar o
Chrome. `--no-parallel` desativa até a thread de música quando `images` não está no plano.

A fase `images` processa uma imagem por vez (`fetch_images.py --single`) com quarentena
de até 4 loops. O stdout do `gemini_fetch` vai **ao vivo** para o log (não é capturado).
Cada imagem emite `== IMAGEM i/N: <nome>` — LiveStrip, rail do Criar e Painel Executivo
acompanham esse contador.

### Layout de um projeto
```
projects/<slug>/
├─ project.json                # checkpoints {fase: {done, ts, detail}} + historico
├─ artifacts/                  # script.json, scenes.json, image_prompts.json,
│                              # narration_timing.json, timeline.json
├─ scenes/s*.html              # overlays de texto (gerados a partir do roteiro)
├─ assets/images/gemini/scenes/ (originais ~2752x1536)
├─ assets/audio/narration/     # s1.mp3 .. sN.mp3
├─ assets/audio/narration_full.wav / final_mix.m4a
├─ assets/audio/gemini/bgm_gemini.wav
├─ composition.html            # composição deste projeto (idêntica ao index.html do render)
└─ output/<slug>.mp4           # ENTREGA FINAL
```

Slug: `slugify()` do prompt (remove acentos/pontuação, minúsculas, 40 chars). "Vídeo engraçado sobre buldogue inglês comportamento e cuidados" → `video-engracado-sobre-buldogue-ingles-co`.

> **Espaço de trabalho HyperFrames compartilhado:** antes de renderizar, `render.ps1` copia `composition.html` → `hyperframes-workspace/index.html` e `final_mix.m4a` → mesma pasta. Um projeto de cada vez.

---

## 2. Requisitos

- Windows 10/11; Python do projeto `C:\videomaker\.venv` (com `edge-tts`, `playwright`, `numpy`, `faster-whisper`).
- FFmpeg `C:\videomaker\ffmpeg\bin` (caminho em `config.json → ffmpeg_dir`).
- Node.js + HyperFrames no `hyperframes-workspace/` (o `package.json` fixa a versão).
- Para as fases de IA (script/images/music): **Chrome logado no Google** com CDP na porta 18800 e perfil dedicado:

```powershell
# login único (não automatize email/senha) — abre o Chrome para você entrar na conta
python C:\videomaker\scripts\gemini_fetch.py --login

# teste rápido (deve responder ok)
python C:\videomaker\scripts\gemini_fetch.py --check
```

Perfil: `C:\videomaker\.chrome-gemini-profile`; CDP `http://127.0.0.1:18800`. Se a sessão cair (exit 4) rode `--login` de novo; se o Chrome não estiver rodando (exit 3), abra-o com `--remote-debugging-port=18800`.

Preparar o shell:
```powershell
$env:PATH = "C:\videomaker\ffmpeg\bin;" + $env:PATH
cd C:\videomaker
```

---

## 3. Como usar o pipeline

### 3.1 CLI — `scripts/pipeline.py`

```powershell
# NOVO projeto completo (10 fases; os checkpoints permitem reexecutar sem repetir nada)
python scripts/pipeline.py full --prompt "Vídeo educativo sobre banho em cachorro"

# retomar projeto existente (usa checkpoints; aceita --from/--only/--skip/--force/--no-parallel/--duration)
python scripts/pipeline.py resume --slug video-educativo-sobre-banho-em-cachorro --no-parallel --duration 590

# status dos checkpoints (audita arquivos fisicamente: JSON válido, contagens, tamanhos)
python scripts/pipeline.py status --prompt "<prompt>"

# reset de checkpoints (arquivos físicos são mantidos)
python scripts/pipeline.py reset --prompt "<prompt>" --phase narration          # uma ou várias, separadas por vírgula
python scripts/pipeline.py reset --slug <slug> --all                          # todas as fases
```

**Seleção de fases (mutuamente exclusivos):**
- `--from auto` (padrão) — roda a partir da primeira fase sem checkpoint válido.
- `--from narration` — roda `narration` → ... → `render`, pulando checkpoints válidos anteriores.
- `--only mix,compose` — roda exatamente essas fases (checkpoint simples das listadas, não invalida nada).
- `--skip script,scenes,images,music` — roda o resto; útil para refazer só etapas locais com os assets de IA já existentes.
- `--force` — refaz as fases do plano ignorando checkpoints (uso conjunto com `--from/--only`).

**Opções:**
| Flag | Default | Efeito |
|------|---------|--------|
| `--voice` | `pt-BR-ThalitaNeural` | voz Edge-TTS |
| `--rate` | `+12%` | velocidade da voz (positiva = mais energia) |
| `--pitch` | `+8Hz` | tom (acima de +15Hz fica artificial) |
| `--style` | `excited` | **não usado** (era SSML; mantido só por compatibilidade de CLI) |
| `--wait` | `240` | timeout por item do Gemini web (s) |
| `--pause` | `8` | pausa entre itens do Gemini (s) |
| `--workers` | `4` | paralelismo da narração |
| `--provider` | `gemini` | `procedural` = trilha offline |
| `--gain` | — | sobrescreve `music.gain` no mix |
| `--duration` | `config.json` | duração alvo do vídeo (s); sobrescreve `target_duration_s` |
| `--no-parallel` | off | desativa thread da música (evita conflito Chrome CDP) |

### 3.2 Invalidação em cascata (chave do fluxo)
Quando uma fase **roda de novo** (por reset manual ou `--force`), as fases que dependem dela são **caducadas automaticamente** no checkpoint — o próximo `full` as re-executa em cima dos dados novos. Ex.: reset `narration` → caducam `timeline`, `mix`, `compose`, `render`. Reset `music` → derruba `render` (a trilha entra no mix). Fases independentes (ex.: `images`) não derrubam as que não a usam.

> Regra prática: editou algo (script.json, scenes/*.html, imagem…)? Rode `reset --phase <fase que gera isso>` e depois `full` — o pipeline re-executa exatamente o que precisa, na ordem correta.

### 3.3 UI Tkinter — `scripts/pipeline_ui.py`

```powershell
python scripts/pipeline_ui.py -p "<prompt>"
```

Barra lateral: **Criar / Publicar / Diário / Executivo / Atividade / Ajustes**.

- **Criar:** prompt + preview do slug, chips das 10 fases, modo `auto/from/only/skip`,
  força, sem paralelismo, pular lint, duração, voz.
- **Gerar vídeo** = `pipeline.py full`; **Retomar** = `resume` pelos checkpoints.
- **Parar** mata a **árvore de processos** (`taskkill /F /T /PID`) — derruba gemini/ffmpeg juntos.
- **Parar tudo** idem + agentes externos (`daily_runner.py` / `pipeline.py` avulsos).
- **Diário:** fila de tópicos, dry-run, forçar hoje, liberar fila, reenviar falhos,
  parar agente, calendário de agendamento (`C:\videomaker\scheduled_videos.json` —
  arquivo único compartilhado com a UI web e o scheduler do backend).
- **Executivo:** KPIs locais (projetos, concluídos, sucesso, duração média, próximo disparo),
  fases do projeto recente, banner de agente externo. Atualiza a cada 5 s enquanto aberta.
- **Atividade:** log ao vivo do subprocesso.
- **Publicar:** YouTube (manual/auto/perguntar), visibilidade, thumbnail, agendar publicação, **atualizar metadados de vídeo existente** (título, descrição, tags, thumbnail via `--yt-video-id`).
- Zoom A+/A-/reset (`Ctrl+=`, `Ctrl+-`, `Ctrl+0`); tema claro/escuro automático.
- Configurações persistidas em `scripts/pipeline_ui_settings.json`.

> Esta UI **não** passa `--promo-first` (flag fantasma removida).
> Calendário de agendamento **só dispara com o backend no ar** (`http://127.0.0.1:8765`).
> A tkinter mostra no Diário se o backend está online ou offline.

### 3.4 UI Web Premium — React + FastAPI

```powershell
# backend
C:\videomaker\run_ui_premium.ps1
# ou
.\.venv\Scripts\python.exe server\api.py        # http://127.0.0.1:8765
cd ui; npm run dev                              # http://localhost:5173
```

Páginas: Criar, Publicar, Diário, Testes, Atividade, **Executivo**, Ajustes.

- Barramento único de execução (`useRunBus`): um WebSocket, run ativo compartilhado.
  **LiveStrip** aparece em todas as páginas quando há vídeo sendo produzido
  (tema, fase, `imagem i/N`, tempo, link para logs). Trocar de página não perde o estado.
- Logs ao vivo por WebSocket `ws://127.0.0.1:8765/api/logs`, com hidratação de
  histórico em `GET /api/logs/recent`.
- Fase `images` emite `== IMAGEM i/N` e o stdout do `gemini_fetch` vai direto ao log
  (não é mais capturado). O visor acompanha o download de verdade.
- Painel Executivo: KPI tiles, gauges por fase (fase corrente do run ativo),
  waterfall, sparkline de durações, histograma de logs/min, countdown,
  banner de agente externo, **Parar run / Parar tudo / Parar agente**.
  Sem run ao vivo, gauges/waterfall ficam rotulados como **histórico** (último projeto),
  não como execução atual.
- Stop real: `POST /api/pipeline/stop/{run_id}` e `/api/pipeline/stop-all`
  usam `taskkill /F /T /PID` na árvore.
- Swagger: `http://127.0.0.1:8765/docs`.

---

## 4. Passo a passo manual (equivalência das fases)

Todos os scripts aceitam `--proj <pasta-do-projeto>`; a ordem abaixo equivale a um `full`:

```powershell
$slug = "meu-projeto"; $proj = "projects\$slug"

python scripts/generate_script_from_prompt.py --prompt "..." --out "$proj\artifacts\script.json"
python scripts/generate_scenes_and_prompts.py --script "$proj\artifacts\script.json" `
    --scenes-out "$proj\artifacts\scenes.json" --prompts-out "$proj\artifacts\image_prompts.json"
python scripts/generate_scene_htmls.py --script "$proj\artifacts\script.json" `
    --scenes "$proj\artifacts\scenes.json" --out-dir "$proj\scenes"

python scripts/fetch_images.py      --proj "$proj"
python scripts/fetch_music_gemini.py --proj "$proj"
python scripts/gen_narration_edge.py --proj "$proj"

python scripts/build_timeline.py    --proj "$proj"
python scripts/mix_audio.py         --proj "$proj" --hf-dir "hyperframes-workspace"
python scripts/build_composition.py --proj "$proj"
python scripts/preprocess_images.py --proj "$proj" --hf-dir "hyperframes-workspace"

powershell -ExecutionPolicy Bypass -File scripts/render.ps1 `
  -ProjectDir "$proj" -Slug "$slug" `
  -CompFile "$proj\composition.html" -MixFile "$proj\assets\audio\final_mix.m4a"
```

Na dúvida, use `python scripts/pipeline.py full --prompt "..."` — ele resolve ordem, paralelismo, checkpoints e cascata.

---

## 5. Referência dos scripts

| Script | O que faz |
|--------|-----------|
| `pipeline.py` | orquestrador; comandos `full/resume/status/reset`; cascata de invalidação; `status` valida arquivos fisicamente; cada fase imprime `== FASE <nome>: iniciando` |
| `pipeline_ui.py` | janela tkinter (prompt, fases, voz, status/parar); sem dependências |
| `generate_script_from_prompt.py` | roteiro via Gemini web (`gemini_fetch.py --kind text`), 2 tentativas, JSON estruturado |
| `generate_scenes_and_prompts.py` | divide o roteiro em cenas; gera prompts de imagem estilo Pixar/Disney 3D |
| `generate_scene_htmls.py` | gera os overlays `s*.html` (texto na tela por cena); **sem chips por padrão**, `--chips` reativa |
| `fetch_images.py` | baixa as imagens do Gemini uma por uma (`--single`); quarentena de falhas no pipeline |
| `fetch_music_gemini.py` | trilha instrumental do Gemini; valida MP4 > 100 KB antes de extrair o WAV |
| `gen_music_procedural.py` | trilha offline procedural (fallback sem internet) |
| `gen_narration_edge.py` | narração Edge-TTS local; **texto puro** e **sem risadas escritas** (ver §7) |
| `build_timeline.py` | normaliza (−16 LUFS), aplica `narration_tempo`, concatena com `gap_seconds`, grava `timeline.json` |
| `mix_audio.py` | loop da trilha com crossfade + ducking sidechain; loudnorm −14 LUFS / −1,5 dBTP |
| `build_composition.py` | monta `composition.html` (câmera, animações GSAP, crossfade `XFADE=0.9s`); timelines pausadas, determinístico |
| `preprocess_images.py` | corta para 1920x1080, copia para o projeto HyperFrames |
| `render.ps1` | `npm run check` → `npm run render` → copia o MP4 → `verify_output.py --proj` |
| `verify_output.py` | STATUS OK se 1920x1080 e |dur − timeline| < 2,0s; loudness |
| `make_contact_sheet.py` | grade de frames para QA visual |
| `verify_narration.py` | (fora do pipeline v3) conferência roteiro × áudio transposto |
| `gemini_fetch.py` | scraping genérico do Gemini web (imagem/texto/áudio/vídeo) via CDP |

---

## 6. `scripts/config.json`

| Campo | Valor | Significado |
|-------|-------|-------------|
| `project_dir` | `".."` | base para `--proj` ausente |
| `voice` / `voice_rate` / `voice_pitch` | `pt-BR-ThalitaNeural` `/ +12% / +8Hz` | defaults do Edge-TTS (o pipeline sobrepõe com `--voice/--rate/--pitch`) |
| `rate_by_pace` | `{slow: -19%, measured: -12%, conversational: -8%, brisk: -3%, fast: 0%}` | ajuste por `delivery_cues.pace` da seção |
| `rate_overrides` | `{}` | ajuste por seção (id → rate) |
| `narration_tempo` | `0.92` | desacelera a narração sem mudar o tom (8%) |
| `gap_seconds` | `1.0` | pausa entre seções na timeline |
| `target_duration_s` | `590` | meta informativa (v3 segue a narração real) |
| `music.gemini_prompt` | genérico ("musica instrumental divertida…") | fallback; o pipeline deriva o prompt do tema do projeto |
| `music.gain` | `0.42` | volume da trilha |
| `music.duck_threshold / ratio / attack_ms / release_ms` | `0.04 / 6 / 25 / 700` | ducking suave (release 700 ms evita "bomba" entre falas) |
| `loudness.narration_i / final_i / true_peak / lra` | `-16 / -14 / -1.5 / 11` | alvos de loudness |
| `video.width / height / fps` | `1920 / 1080 / 30` | resolução |
| `ffmpeg_dir` | `C:\videomaker\ffmpeg\bin` | FFmpeg |
| `gemini_skill` | `...\gemini-media-scraping\gemini_fetch.py` | localização do scraper |

> Chave `tts.*` (provider/model/voice/chunks/laughs) é **legado** — fluxo antigo do Gemini TTS (quota 10 req/dia). Não usada pelo v3.

---

## 7. Regras de qualidade da narração (lições importantes)

1. **Sem SSML.** O Edge-TTS lê as tags em voz alta ("speak version 1.0 xml lang…"). `gen_narration_edge.py` usa texto puro; `--style` é aceito e ignorado.
2. **Sem risadas escritas** ("Hahaha!", "ha ha ha"): soam falsas/forçadas em vozes neurais. O script remove automaticamente (`LAUGH_RE`). A energia vem de `rate`/`pitch` + pontuação do roteiro.
3. Não escreva instruções de estilo no `text` ("fale com alegria") — nenhuma TTS interpreta instrução; ela lê a frase literal.

---

## 8. Como alterar um projeto existente

| O que mexeu | Faça |
|-------------|------|
| Texto da narração (`script.json`) | `reset --phase narration` → `full` (cascata re-refaz timeline/mix/compose/render) |
| Voz/rate/pitch | `reset --phase narration` → `full --voice ... --rate ... --pitch ...` |
| Overlays na tela (`projects/<slug>/scenes/sN.html`) | regenere com `generate_scene_htmls.py` (sem `--chips`) → `reset --phase compose` → `full`; guia detalhado em `MANUAL_GRAFOS.md` |
| Prompts de imagem | aponte `image_prompts.json` + `reset images` (ou só a(s) imagem(ns) via `fetch_images.py --only`) |
| Música | `config.json → music.gemini_prompt` + `reset music` (ou `--provider procedural`) |
| Transições/duração (`XFADE`, `gap_seconds`) | `reset compose` (XFADE) ou `reset timeline` (gap) → `full` |
| Duração alvo do vídeo | `--duration 600` no `full`/`resume` (atualiza `config.json` e afeta trilha/mix) |

Downstream é sempre refeito via cascata — não é preciso lembrar de renderizar.

---

## 8.5 Atualizar metadados de vídeo já enviado ao YouTube

Você pode atualizar **título, descrição, tags, categoria e thumbnail** de um vídeo que já está no YouTube sem reenviar o MP4. Útil para corrigir erros, melhorar SEO ou trocar a miniatura.

### Via CLI (`pipeline.py`)
```powershell
# Atualiza apenas metadados (não faz upload de vídeo novo)
python scripts/pipeline.py full --slug <slug> `
    --yt-video-id <ID_DO_VIDEO_YOUTUBE> `
    --yt-title "Novo título" `
    --yt-desc "Nova descrição completa" `
    --yt-tags "tag1,tag2,tag3" `
    --yt-thumb "caminho\para\miniatura.jpg" `
    --yt-secret "caminho\para\client_secret.json"
```

Se omitir `--yt-title`, `--yt-desc` ou `--yt-tags`, o pipeline usa os valores salvos em `config.json` (seção `youtube`) ou o prompt do projeto como fallback.

### Via UI Web (Página Publicar)
1. Abra a página **Publicar** na UI web.
2. No campo **ID do vídeo existente**, cole o ID do vídeo do YouTube (ex: `3vqti6cJ3EE` da URL `https://youtu.be/3vqti6cJ3EE`).
3. Preencha Título, Descrição, Tags, Categoria, Visibilidade, Thumbnail e client_secret.json.
4. Clique em **Enviar ao YouTube** — o pipeline chama `youtube_update.py` que atualiza apenas o snippet do vídeo existente.

> Na primeira execução o navegador abre para autorizar o canal (OAuth2). O token fica salvo em `scripts/youtube_token.json`.

---

## 9. QA

| Comando | Esperado |
|---------|----------|
| `python scripts/pipeline.py status --prompt "..."` | 10 fases `OK (checkpoint)` |
| `python scripts/verify_output.py --proj projects\<slug>` | STATUS OK; loudness ~−14 LUFS |
| `npx hyperframes lint` (no projeto HyperFrames) | 0 erros |
| `python scripts/make_contact_sheet.py --at 10,60,120,250 --cols 3` | grade sem frames pretos |
| Escutar 3 trechos (início/meio/fim) | sem jargão, sem risada forçada, sem corte de fala |

---

## 10. Solução de problemas

| Problema | Causa / solução |
|----------|-----------------|
| `RuntimeError: FASE ... exit 2` | argumento de CLI inconsistente — v3 aceita `--style` inofensivamente; atualize os scripts |
| Checkpoint diz `done` mas o artefato tá velho | algo foi editado depois do checkpoint — `reset` a fase que gera esse artefato; a cascata cuida do resto |
| Jargão "speak version 1.0 xml" na voz | bug de SSML antigo, corrigido — use `gen_narration_edge.py` e confirme que não há SSML |
| Risada forçada/fake | já filtrado (`LAUGH_RE`); se sobrar, edite o `script.json` e reset `narration` |
| Render lento | normal: ~5 min de vídeo ≈ 12 min de render em CPU; 5 workers do Chrome em screenshot |
| `gemini_fetch` exit 3 | Chrome fora da porta CDP 18800 — abra com `--remote-debugging-port=18800` |
| `gemini_fetch` exit 4 | sessão de login expirada — rode `--login` |
| Música engasga entre falas | aumente `music.duck_release_ms` (≥700) |
| Transição abrupta entre cenas | mantenha `XFADE = 0.9` no `build_composition.py` |
| Texto não sobrepõe | verifique `scripts/scenes/sN.html` — a classe `.block` + `data-at` controla posição/entrada |
| `images` e `music` falham juntas (timeout/erro CDP) | competem pelo mesmo Chrome; o pipeline já roda `music` antes de `images` quando ambas estão no plano; se ainda assim ocorrer, use `--no-parallel` |
| Log em "cenas" enquanto baixam fotos | run antigo (pré-v3.4) ainda em memória — o próximo `full` emite `== FASE images` e `== IMAGEM i/N` ao vivo |
| Agendamento da tkinter não disparou | arquivo unificado agora é `C:\videomaker\scheduled_videos.json`; backend precisa estar no ar (`/api/health`); a tkinter avisa se estiver offline |
| `unrecognized arguments: --promo-first` | flag fantasma que não existe mais — atualize UI/API (já removida); não passe a flag na mão |
| Painel Executivo sem logs / sem fase atual | confirme backend na porta 8765; WS em `ws://127.0.0.1:8765/api/logs`; histórico em `/api/logs/recent` |
| Painel Executivo mostra fases prontas antes de iniciar | você está vendo o **histórico** do último projeto (título "sem execução ao vivo"); ao disparar um run, os gauges reiniciam |
| Imagem corrompida (0 bytes) no preprocess | `reset --phase images` → `resume --no-parallel` — a cascata invalida `preprocess` e `render` |

---

## 10.5. Autenticação do YouTube (OAuth2)

Para enviar vídeos ou atualizar metadados no YouTube, é necessário autenticar o canal via OAuth2. Dois arquivos são usados:

| Arquivo | Descrição |
|---------|-----------|
| `scripts/client_secret.json` | Credenciais OAuth do projeto Google Cloud |
| `scripts/youtube_token.json` | Token de acesso/refresh (gerado após autorização, não compartilhar) |

### Como obter o `client_secret.json`

1. Acesse https://console.cloud.google.com
2. Crie ou selecione um projeto
3. Ative a **YouTube Data API v3** (Biblioteca)
4. Em **Credenciais**, crie um **ID do cliente OAuth** (tipo: App para computador)
5. Baixe o JSON e salve como `scripts/client_secret.json`
6. Em **Tela de consentimento OAuth**, adicione seu e-mail como **Usuário de teste**

### Rodar a autenticação

```powershell
# Setup inicial (gera o token):
& .\.venv\Scripts\python.exe scripts/youtube_setup.py

# Trocar de canal (força nova autorização):
& .\.venv\Scripts\python.exe scripts/youtube_setup.py --reset-token
```

Após autorizar no navegador, o token fica salvo em `scripts/youtube_token.json` e é reusado por `youtube_upload.py` e `youtube_update.py`.

### Scripts relacionados

| Script | Função |
|--------|--------|
| `youtube_setup.py` | Setup/autenticação OAuth (gera o token) |
| `youtube_upload.py` | Envia vídeo novo para o YouTube |
| `youtube_update.py` | Atualiza metadados de vídeo existente |
| `pipeline.py` | `--yt-video-id` para atualizar metadados após o render |

---

## 11. Checklist de entrega

- [ ] `pipeline.py status` → 10/10 fases OK
- [ ] `output/<slug>.mp4` existe e `verify_output.py --proj` → STATUS OK
- [ ] 1920x1080 @30, H.264 + AAC, ~−14 LUFS / ≤ −1,5 dBTP
- [ ] `npx hyperframes lint` → 0 erros
- [ ] Sem jargão SSML e sem "Hahaha" na narração
- [ ] Contact sheet revisada: painéis não cobrem o rosto, sem frames pretos
- [ ] Durante `images`, o log mostra `== IMAGEM i/N` e o stdout do gemini_fetch (não fica preso em "cenas")
- [ ] LiveStrip aparece em Criar/Diário/Executivo/Atividade durante o run
- [ ] Painel Executivo sem run mostra "histórico", não finge que é ao vivo

---

## 12. Determinismo

- **100% local/determinístico:** `scenes`, `narration` (Edge-TTS), `timeline`, `mix`, `compose`, `preprocess`, `render`.
- **Não determinístico (Gemini web):** `script`, `images`, `music` — variam por execução; os checkpoints evitam repetições desnecessárias.
- Para reproduzir byte a byte um vídeo entregue: mantenha os assets e rode só as fases locais (`full --auto` — os checkpoints estarão completos; ou `--skip script,scenes,images,music,narration`).

---

## 13. Arquivos envolvidos

```
scripts/          config.json, pipeline.py, pipeline_ui.py,
                  generate_script_from_prompt.py, generate_scenes_and_prompts.py,
                  generate_scene_htmls.py, fetch_images.py, fetch_music_gemini.py,
                  gen_music_procedural.py, gen_narration_edge.py, build_timeline.py,
                  mix_audio.py, build_composition.py, preprocess_images.py,
                  render.ps1, verify_output.py, make_contact_sheet.py,
                  verify_narration.py, gemini_fetch.py, scenes.json, scenes/s*.html,
                  daily_runner.py, topics.txt, youtube_upload.py, youtube_update.py,
                  youtube_setup.py, generate_thumbnail.py
server/api.py     FastAPI: REST + WS de logs, telemetry, stop tree, scheduler
ui/src/           App.jsx, services/api.js, hooks/useRunBus.jsx, index.css
ui/src/hooks/     useRunBus.jsx (WS único + run ativo compartilhado)
projects/<slug>/  project.json, artifacts/, scenes/, assets/, composition.html, output/
hyperframes-workspace/  index.html, package.json, meta.json, node tooling
```
