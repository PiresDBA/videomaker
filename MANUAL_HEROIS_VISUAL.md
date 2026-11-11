# 🦸‍♂️ MANUAL VISUAL — Videomaker (Edição Cartoon Super-Heróis)

> **Feito para quem tem TDH e aprende melhor com cores, imagens (em texto) e blocos curtos.**
> Nenhum parágrafo longo. Tudo dividido em "poderes", "heróis" e "batalhas".
> Se algo estiver aqui, **já foi feito**. Não refaça. Não desfaça.

---

## 🎯 O que é este sistema?

É uma **fábrica de vídeos animados** para o YouTube.  
Você dá o tema (prompt), e uma equipe de 10 heróis gera o vídeo sozinha, do roteiro ao MP4 final.

```
VOCÊ (Prompt)  ──►  10 HERÓIS (fases do pipeline)  ──►  VÍDEO .mp4 (output/)
```

---

## 🦸‍♀️ Você = O Comandante

Seu superpoder é escrever o **prompt** (o tema do vídeo).

| Seu comando | O que faz |
|-------------|-----------|
| `full` | Cria o projeto do zero e roda tudo até o fim. |
| `resume` | Retoma um projeto que parou no meio (não recomeça do zero). |
| `status` | Mostra o que já foi feito e o que falta. |
| `reset` | Apaga o "checkpoint" de uma fase para refazê-la (os arquivos ficam no disco). |
| `contract` | Mostra as regras de ouro (leia antes de começar). |

Exemplo de lançamento:

```powershell
python scripts/pipeline.py full --prompt "Frida e Luna na fazenda em Minas Gerais" --slug frida-luna-fazenda
```

---

## 🛡️ A Liga dos 10 Heróis (Pipeline)

Cada herói tem um **poder**, uma **saída** e uma **ordem** fixa. Eles não pulam a vez.

```
1. script      → 2. scenes  → 3. music  → 4. images  → 5. narration
   6. timeline  → 7. mix    → 8. compose → 9. preprocess → 10. render
                                                        │
                                                    11. youtube (só se você pedir --publish)
```

### Herói 1 — script 📝
**Poder:** escreve o roteiro em JSON (`artifacts/script.json`).  
**Inimigo:** texto duplicado, frases que não existem.  
**Arma:** `generate_script_from_prompt.py` + Gemini Web (Chrome CDP).  
**Regra:** ordem fixa das seções: `s_intro → s0 → s1… → s_final → s_outro`.

### Herói 2 — scenes 🎬
**Poder:** divide o roteiro em cenas e cria prompts de imagem (`scenes.json`, `image_prompts.json`).  
**Inimigo:** cenário mudando de cena para cena (grama se o tema é Marte!).  
**Arma:** `generate_scenes_and_prompts.py`.  
**Nota:** se mudar de tema, resete **scenes** junto com **images**.

### Herói 3 — music 🎵
**Poder:** cria a trilha sonora (`bgm_procedural.wav` ou do banco local).  
**Inimigo:** música com narração já embutida (narração sobre narração).  
**Arma:** `gen_music_procedural.py` / `mix_audio.py`.  
**Sempre roda ANTES de images** (para não brigar com o Chrome).

### Herói 4 — images 🖼️
**Poder:** gera ou busca as imagens de cada cena.  
**Ordem de busca:** banco local (BM25) → Google Flow → Gemini Web (fallback).  
**Quarentena:** se uma imagem falhar, tenta até **4 vezes** antes de desistir.  
**Arma:** `fetch_images.py`, `flow_fetch.py`, `gemini_fetch.py`.

### Herói 5 — narration 🗣️
**Poder:** transforma texto em áudio (narração).  
**Vozes:** Gemini TTS (Achernar/Leda, com rotação de 5 chaves de API) → fallback Edge-TTS (ThalitaNeural).  
**Inimigo:** narração duplicada (mesma frase falada duas vezes).  
**Defesa:** `faster-whisper` confere o áudio e regenera se houver repetição.  
**Arma:** `gen_narration_gemini_sections.py`, `gen_narration_edge.py`.

### Herói 6 — timeline ⏱️
**Poder:** normaliza os MP3s, concatena com pausas e grava `timeline.json` com início/fim de cada seção.  
**Inimigo:** duração incorreta (áudio e vídeo desencontrados).  
**Regra de ouro:** se mudar narração ou timeline, **deve** reexecutar `compose` depois.

### Herói 7 — mix 🔊
**Poder:** mistura narração + trilha (`final_mix.m4a`).  
**Inimigo:** narração 4 segundos adiantada em relação às imagens.  
**Defesa:** lead-in de 4s de trilha na capa para alinhar tudo.

### Herói 8 — compose 🧩
**Poder:** monta o `composition.html` (o desenho do vídeo com overlays, câmera, imagens).  
**Inimigo:** chips de palavras poluindo a tela (desativados por padrão; só com `--chips`).  
**Arma:** `build_composition.py`.

### Herói 9 — preprocess 📦
**Poder:** copia imagens para o workspace do HyperFrames (redimensiona JPGs; MP4s vão intactos).  
**Arma:** `preprocess_images.py`.

### Herói 10 — render 🎥
**Poder:** gera o MP4 final em `output/<slug>.mp4`.  
**Regra:** nunca sobrescreve o original; use um `-Slug` diferente para variantes.  
**Arma:** `render.ps1` (com `-SkipCheck` para pular lint se já validou antes).

### Herói 11 — youtube 📺 (opcional, só com `--publish`)
**Poder:** publica no YouTube com título, descrição (padrão oficial do canal, 100+ palavras), tags, thumbnail e "feito para crianças".  
**Arma:** `youtube_upload.py` + `description_template.py`.  
**Obs:** se todos os checkpoints já estiverem prontos, `full --publish` não faz nada; use o uploader direto.

---

## 🏰 O Quartel General — Projetos e Checkpoints

Cada vídeo fica em sua própria base secreta:

```
projects/<slug>/
├── project.json                 ← diário de bordo (checkpoints: o que já foi feito)
├── project-control.json         ← relatório final (duração, tamanho, publish)
├── artifacts/
│   ├── script.json              ← roteiro (Herói 1)
│   ├── scenes.json              ← cenas (Herói 2)
│   ├── image_prompts.json       ← prompts de imagem (Herói 2)
│   ├── narration_timing.json    ← durações da narração (Herói 5)
│   └── timeline.json            ← início/fim de cada seção (Herói 6)
├── scenes/sN.html               ← overlays de texto de cada cena (Herói 8)
├── assets/images/gemini/scenes/*.jpg   ← imagens (Herói 4)
├── assets/audio/...             ← narração, trilha, mix (Heróis 3, 5, 7)
├── composition.html             ← desenho do vídeo (Herói 8)
└── output/<slug>.mp4            ← VÍDEO FINAL (Herói 10)
```

**Checkpoint:** quando um herói termina, grava "feito" no `project.json`. Se o pipeline parar, `resume` continua de onde parou.

---

## 🖥️ O Quartel General Móvel — Pipeline UI (Tkinter)

Janela local para quem não quer usar linha de comando.

| Página | Função |
|--------|--------|
| Criar | prompt, duração, voz, geração do vídeo |
| Publicar | envio ao YouTube (título, descrição, tags, privacidade) |
| Diário | executor diário (fila de tópicos, run, dry-run, unpause) |
| Executivo | KPIs, fases do projeto recente, countdown, parar tudo / parar agente |
| Ajustes | tema, zoom, atalhos |

**Atalhos:**
- `Ctrl + Enter` → gerar vídeo (página Criar)
- `Ctrl + + / - / 0` → zoom da interface
- `stop` usa `taskkill /F /T /PID` (mata o pipeline e todos os filhos: gemini, ffmpeg)

---

## 🚀 A Nave Espacial — UI Web (React + FastAPI)

Interface moderna no navegador.

```
Navegador (React + Vite, porta 5173)  ⇄  API FastAPI (porta 8765)  ⇄  scripts/pipeline.py
```

| Página | O que faz |
|--------|-----------|
| Criar | prompt, trilho das 10 fases, seleção de etapas, duração, voz, upload YouTube |
| Publicar | lista de projetos + formulário completo do YouTube + file picker de MP4 |
| Diário | calendário mensal, agendar vídeos, recorrência, tópicos disponíveis |
| Testes | modo teste (todas as etapas rápido) + retomada de qualquer ponto |
| Atividade | logs em tempo real via WebSocket (`/api/logs`) |
| Executivo | KPIs, gauges por fase, waterfall do run ativo, sparkline de durações |
| Ajustes | tema claro/escuro/automático, zoom |

**LiveStrip:** aparece em todas as páginas quando há um vídeo sendo gerado — mostra tema, fase atual, detalhe (ex: "imagem 3/12") e tempo.

**Launcher:**
```powershell
C:\videomaker\run_ui_premium.bat   # duplo-clique
# ou
C:\videomaker\run_ui_premium.ps1
```

URLs depois de iniciar:
- Frontend: `http://localhost:5173`
- Backend API: `http://127.0.0.1:8765`
- Docs automática: `http://127.0.0.1:8765/docs`

---

## 📡 O Comando (API do backend)

| Endpoint | O que faz |
|----------|-----------|
| `GET /api/health` | está vivo? |
| `POST /api/pipeline/run` | roda o pipeline completo |
| `POST /api/pipeline/resume` | retoma projeto existente |
| `GET /api/pipeline/status/{id}` | status de uma execução |
| `GET /api/pipeline/runs` | execuções ativas |
| `POST /api/pipeline/stop/{id}` | interrompe execução |
| `GET /api/projects` | lista projetos |
| `GET /api/projects/{slug}/status` | checkpoints de um projeto |
| `POST /api/daily/run` | executor diário |
| `GET /api/daily/status` | fila diária |
| `GET /api/schedules` | agendamentos |
| `GET /api/topics` | tópicos da fila |
| `WS /api/logs` | logs ao vivo (WebSocket) |

---

## ⚔️ O Inimigo — Problemas comuns e como derrotar

| Sintoma | Solução (superpoder) |
|---------|----------------------|
| Chips voltaram nas cenas | rode §7.1 (sem `--chips`) e depois §7.3 (rebuild compose) |
| Render sobrescreveu o vídeo original | use `-Slug` diferente |
| Vídeo com duração errada / delta != 0 | mudou narração/timeline? rode `compose` antes de `render` |
| `NameError: name 'sp' is not defined` | já corrigido no `pipeline.py` |
| Gemini TTS sem cota (429) | rotação de chaves (`GOOGLE_TTS_API_KEY_1…_3`) ou fallback Edge-TTS |
| `.env` em UTF-16 quebrando chaves | leitura via `scripts/env_keys.py` (detecta BOM) |
| `composition.html` antigo após editar `scenes.json` | `reset --phase compose` antes de `resume --from compose` |

---

## 🔄 O Ritmo da Batalha (dependências em cascata)

Quando um herói é refeito, os abaixo dele ficam pendentes automaticamente:

```
script ──► scenes ──► preprocess
   │          │          │
   │          └──► compose ──┐
   │                         │
   └──► narration ──► timeline ──► mix ──┐
                      │       │          │
                      └───────┴──────────┴──► render
                      │                  ▲
                      └──────► compose ──┘
                      music ──► mix ───────┘
                      images ──► preprocess ─┘
```

**Leitura prática:**
- Mexeu no roteiro → `reset --phase script` → `full` refaz o resto.
- Mexeu nos overlays → `reset --phase scenes` ou `compose` → `full`.
- Trocou a trilha → `reset --phase music` → `full` (refaz mix e render).
- Quer só uma variante → renderize com outro `-Slug`.

---

## 📋 Checklist antes de publicar

- [ ] `scenes/sN.html` sem `class="chip"` (padrão sem chips).
- [ ] `composition.html` sem `class="chips"`/`class="chip"`.
- [ ] Texto na esquerda legível, sem cobrir o rosto de Frida ou Luna.
- [ ] `verify_output.py` retorna `STATUS OK`.
- [ ] Conferir frame no início, meio e fim do vídeo.
- [ ] `python scripts/check_manual.py` (manual em dia com o código).
- [ ] `python scripts/smoke_test_description.py` e `check_projects.py`.

---

## ⚡ Ordem sagrada (nunca quebre)

**branch → código → manual → checks → commit → push**

1. `git checkout -b feature/nome-curto`
2. Faça a mudança.
3. Atualize o `MANUAL_GRAFOS.md` (mesmo commit).
4. Rode os checks.
5. `git add -A && git commit -m "tipo: o que mudou" && git push`

> **O manual é a memória do produto. Se não está no manual, não existe.**

---

## 🦸‍♂️ Resumo em 30 segundos

1. Leia `CONTRATO.md` + `MANUAL_GRAFOS.md` + docstring do `pipeline.py`.
2. Crie branch `feature/...`.
3. Rode o vídeo com `pipeline.py full --prompt "..." --slug ...`.
4. Se precisar parar e continuar, use `resume`.
5. O vídeo sai em `projects/<slug>/output/<slug>.mp4`.
6. Não publique sem pedir (`--publish` é opcional).

---

**Pronto, comandante. Seu vídeo de super-heróis está nas mãos da Liga dos 10 Heróis. 🦸‍♀️💥**