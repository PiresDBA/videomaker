# Manual do Usuário — Videomaker (Canal Frida e Luna)

> Guia de uso diário. Atualizado em 04/11/2026 (v3.7). O manual técnico com grafos
> fica em `MANUAL_GRAFOS.md`. Toda alteração do sistema atualiza os dois.

---

## 1. O que é

Sistema que gera, publica e agenda vídeos animados de dogs ("Frida e Luna") para
o YouTube, do roteiro IA até o MP4 renderizado, com executor diário e painel executivo.

---

## 2. Como iniciar

Dê duplo clique em **`C:\videomaker\run_ui_premium.bat`** (ou rode
`run_ui_premium.ps1`). Ele sobe o backend e o frontend sozinho.

| Serviço | Endereço |
|---|---|
| Interface web | http://localhost:5173 |
| Backend API | http://127.0.0.1:8765 |
| Docs da API | http://127.0.0.1:8765/docs |

Manual (alternativo):
```powershell
cd C:\videomaker
.\.venv\Scripts\python.exe server\api.py    # terminal 1 (backend)
cd ui ; npm run dev                          # terminal 2 (frontend)
```

---

## 3. Páginas da interface

| Página | Para que serve |
|---|---|
| **Criar** | Digita o tema, escolhe as fases e gera o vídeo. O trilho das 10 fases acende em tempo real (verde = feito, âmbar pulsante = fase atual). |
| **Publicar** | Lista de projetos + envio ao YouTube (título, descrição, tags, visibilidade, thumbnail, credenciais OAuth) e **atualização de metadados de vídeo já enviado**. Também aceita MP4 pronto escolhido no disco. |
| **Diário** | Calendário para **agendar** vídeos por data/hora (vários por dia, com recorrência diária/úteis/semanal), fila de tópicos, execução do episódio do dia. |
| **Testes** | Modo teste: roda as 10 etapas rápido (duração reduzida, pula lint) e retomada de qualquer fase informando o slug. |
| **Atividade** | Logs em tempo real (WebSocket) com níveis OK/ERR/WARN/RUN; copiar e limpar. |
| **Executivo** | Painel gerencial: KPIs (projetos, concluídos, tempo médio, próximo disparo), gauges das fases do run ao vivo, waterfall, duração dos projetos, logs por minuto, banner do agente externo com botão Parar. |
| **Ajustes** | Tema (claro/escuro/automático), zoom (75–150%). |

> **Atenção (leitura do Executivo):** título "run ao vivo" = execução em andamento;
> título "com histórico" = último projeto concluído, e não o que você vai iniciar.

---

## 4. Fluxo básico: gerar um vídeo

1. Página **Criar** → escreva o prompt (ex.: "A Frida e a Luna descobrem o aspirador").
2. Confira o trilho das fases → **Gerar** (ou `Ctrl+Enter`).
3. Acompanhe pelo **LiveStrip** (aparece em todas as páginas) ou pela página Criar.
4. Ao terminar, publique em **Publicar** ou espere o agendamento.

Fases do pipeline: `script → scenes → images → music → narration → timeline → mix → compose → preprocess → render`.
O MP4 fica em `projects/<slug>/output/`.

---

## 5. Agendar automático

1. Página **Diário** → escolha a data no calendário.
2. "Agendar novo vídeo": defina a fonte (**Fila automática** — pega o próximo tópico;
   ou **Tópico específico**), data, hora e recorrência.
3. O scheduler dispara sozinho na hora (não dispara se já houver run ativo).
4. Com o botão **Recolocar na fila** você devolve um assunto falho à fila.

---

## 6. Atalhos de teclado

| Tecla | Efeito |
|---|---|
| `Ctrl + Enter` | Gerar vídeo (página Criar) |
| `Ctrl + +` (numérico) | Zoom + |
| `Ctrl + -` (numérico) | Zoom − |
| `Ctrl + 0` (numérico) | Zoom 100% |

---

## 7. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| Página branca / build falhou | `cd ui && npm run build` — se falhar, consultar §29 do `MANUAL_GRAFOS.md` |
| Agendamento não disparou | Confere se o backend está no ar (`/api/health`) e se não há run ativo |
| Quero parar tudo | Botão "Parar tudo" no painel Executivo (mata a árvore de processos) |
| Acentos estranhos na tela | Concatenado ao bug histórico de encoding; reportar para correção no App reconstruído |

---

## 8. Histórico de mudanças (registrar aqui a cada sessão)

| Data | Versão | Mudanças |
|---|---|---|
| 03/11/2026 | v3.5 | Base modular do frontend: primitivas de UI (`components/ui.jsx`), widgets executivos (`execWidgets.jsx`), `PipelineRail`, constantes de fases (`utils/phases.js`), `fmtDuration` (`utils/fmt.js`); `PageExecutivo` reconstruído (JSX corrompido removido, logs com nível); build de produção passando (2,88s). Próximo passo: extrair páginas para `ui/src/pages/`. |
| 04/11/2026 | v3.6 | Pipeline com melhorias de resiliência e engajamento: (1) detecção de duplicidade via `projects-deliveries.json` (não varre pastas; avança para próximo tópico da fila se duplicado); (2) duas imagens por cena (variante A cena principal + variante B close-up/reação, `split: 0.5`); (3) capa sem transição inicial (aparece no primeiro frame) com imagem de fundo e título do episódio lido corretamente do `script.json`; (4) fetcher inteligente com anexo de referência (`referencia.jpg`), detecção precoce de recusa na tela, 4 estratégias de prompt (original → suave → simplificada → genérica) e guarda anti-Vídeo; (5) sanitização de prompts corrigida (não destrói palavras como "de estar"); (6) mix de áudio com fallback automático (gemini → procedural); (7) sincronização automática dos bancos globais (`banco de imagens/` + `banco de músicas/`) após cada entrega; (8) JSON de controle por projeto (`project-control.json`) + JSON global de entregas (`projects-deliveries.json`); (9) upload público no YouTube (`--publish --privacy public --yt-kids`). Smoke tests concluídos: Hachiko (165.6s), Ensinar sentar/pata (183.4s), Saga Osso de Ouro 1/4 (171.5s). Vídeo público: https://youtu.be/d0Zm3_hSmSs |
| 04/11/2026 | v3.7 | Banco de imagens e músicas locais: o pipeline consulta `C:\videomaker\banco de imagens\` (via `indice_midia.db`) e `C:\videomaker\banco de músicas\` **antes** de gerar via Gemini, reutilizando ativos existentes; sincronização automática dos bancos após cada entrega (`scripts/sync_bancos.py`); `projects-deliveries.json` como fonte de verdade de entregas (detecção de duplicidade sem varrer pastas); `scripts/rebuild_deliveries.py` para reconstrução. Narração em português corrigida: todos os textos processados em UTF-8 (acentos, cedilha preservados), abertura ("Olá, amiguinhos! Tudo bem com vocês hoje?") e encerramento ("Muito obrigado por assistir nosso vídeo! ... fiquem com Deus e tchau até o próximo vídeo!") inseridos automaticamente. Upload público no YouTube via `--publish --privacy public --yt-kids`. Smoke tests concluídos: 3 pipelines completos com upload, todos h264 1920×1080@30. |
| 05/11/2026 | v3.8 | Correções críticas de qualidade: (1) **`generate_scene_htmls.py`**: `is_intro_section()` agora só considera `s0` como introdução — cenas com "Apresentação" no rótulo (ex.: "Apresentação da Fridoca") não ganham mais overlay de título indevidamente; (2) **`sync_bancos.py`**: não copia mais `final_mix.m4a` (narração+música) para o banco de músicas, evitando narração sobre narração ao reusar trilhas; (3) **Saudação do canal** alterada para "Olá amiguinhos e amiguinhas! Tudo bem com vocês? Que legal ter vocês aqui com a gente!" (sem vírgula robotizada após "Olá"); (4) **Upload YouTube**: todos os parâmetros agora são **automáticos por padrão** — não precisa passar nada na linha de comando. Descrição automática completa (conteúdo, marcação "gerado por IA", "sem promoção paga", idioma "Português do Brasil", "feito para crianças"), thumbnail automática (procura `thumb.jpg`/`thumbnail.jpg` na pasta do projeto, senão primeira imagem da cena), título pega do `script.json`, idioma `pt-BR` para vídeo e áudio, infantil ativado por padrão. Basta rodar `python scripts/youtube_upload.py --video <caminho.mp4>`. (5) `MANUAL_GRAFOS.md`, `MANUAL_USUARIO.md`, `MANUAL_REFERENCIA.md` e `scripts/README.md` atualizados. |
