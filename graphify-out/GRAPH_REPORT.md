# Graph Report - videomaker  (2026-11-18)

## Corpus Check
- 225 files · ~1,301,983 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: .bat 7, (none) 2, .zip 1)

## Summary
- 2522 nodes · 5157 edges · 166 communities (113 shown, 53 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 360 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0d15b821`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- api.py
- gen_narration_gemini_sections.py
- Publishing & Image Fetch
- Pipeline UI Upload Panel
- description_template.py
- YouTube Audit & Descriptions
- Daily Runner & Prompt Generation
- upload_por_idioma.py
- pipeline.py
- limpar_duplicados_pt.py
- Render Log: Novo Video 7
- Pipeline UI Main Layout
- Debug & Test Utilities
- Gripe Video Story Beats
- json
- os
- Pipeline Phase Functions
- TTS Quota & Voice Checks
- f
- Narration Alignment & Timeline
- Pipeline UI Scheduler
- EN Production Log Concepts
- Character Audit & Translation
- Test & Upload Logs
- flow_agent_batch.py
- Fazenda Pipeline Log
- Manual de Grafos Concepts
- Project
- TTS Fallback & Audio Mix Logs
- flow_mcp.py
- Flow Fetch / Inspect Agent Mode2
- publish_multilang.py
- build_description
- Limpar Duplicados Pt / Listar Canal
- Es
- Loop40
- youtube_metadados.py
- criar_efeitos_final.py
- Contrato / Agents
- Flow Fetch
- Novo Video / Loop Completo5
- criar_efeitos_final_v2.py
- Youtube Metadados / Youtube Upload
- Topics-Old / Topics
- Pipeline Ui-Old
- re
- gen_narration_voicecraft.py
- Flow Fetch
- Youtube Update Guide / Caminha Pt
- Userunbus / Phases
- gen_music_procedural.py
- Prompt Gen - Copia
- subprocess
- Video Espirrinho Google
- match_videos_by_duration.py
- rerender_all_no_text.py
- Build Composition / Mix Audio
- Youtube Batch Publish
- Loop Completo2 / Loop Completo
- Render Bg 1966927817 / Render Bg Err
- generate_thumbnail.py
- atualizar_endscreen.py
- .__init__
- loop40.py
- test_paineis.py
- translate_script.py
- Translate Script
- Video Gripe7
- Manual Grafos / Manual Referencia
- flow_fetch.py
- Match Videos By Duration
- gen_subtitles.py
- .__init__
- canal_match.py
- check_video_idioma.py
- Video Tarzan5 / Readme
- Youtube Captions
- shutil
- fetch_images.py
- atualizar_endscreen_playwright.py
- time
- Gen Subtitles
- _enviar_uma_vez
- check_personagens_imagens.py
- check_texto_idioma.py
- detecta_paineis.py
- check_prompt_repeticao.py
- Flow Fetch
- os
- Relatorio Youtube Idiomas
- Backfill Languages
- unicodedata
- Pipeline
- audit_youtube.py
- Contrato / Agents
- install_hooks.py
- execute_phases
- Build Topics
- Make Contact Sheet
- Pipeline Ui
- Novo Video8
- Manual Grafos
- Manual Usuario
- Pipeline
- Probe Edge Voices
- align_narration.py
- phase_music
- Manual Grafos / Manual Herois Visual
- Readme
- Render.Ps1
- Agents / Contrato
- Pre-Commit
- Fix Bat
- Manual Grafos
- Manual Grafos
- Manual Usuario
- Run Caminha Agent.Ps1
- Run Caminha Pt.Ps1
- Run En.Ps1
- Run Es.Ps1
- Run Flow Beats.Ps1
- vira-lata-caramelo-o-heroi-do-brasil (falhou)
- Saga do Osso de Ouro (4 partes)
- index.html — entry point da UI (React/Vite)
- check_imagens_repetidas.py
- gen_narration.py
- select_topic.py
- diag_modelo.py
- .cal_add_schedule
- CalendarDay
- youtube_captions.py
- pick_hook
- criar_efeitos_teste.py
- phase_images
- sync_bancos.py
- phase_youtube
- argparse
- criar_efeitos_teste_v2.py
- pathlib
- _gemini_tts_key
- loop_upload_idiomas.py
- scripts/make_contact_sheet.py
- criar_efeitos_teste_v3.py

## God Nodes (most connected - your core abstractions)
1. `App` - 90 edges
2. `f()` - 56 edges
3. `P()` - 47 edges
4. `Project` - 33 edges
5. `build_description()` - 22 edges
6. `fnt()` - 20 edges
7. `main()` - 19 edges
8. `main()` - 19 edges
9. `apply_contract()` - 18 edges
10. `load_json()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `update_config()` --indirect_call--> `f()`  [INFERRED]
  setup_reference_image.py → scripts/gen_music_procedural.py
- `narration_contract.py — contrato de abertura/encerramento` --conceptually_related_to--> `Render HyperFrames — vídeo 'depois de assistir o filme do Tarzan'`  [INFERRED]
  scripts/README.md → log_video_tarzan5.txt
- `render.ps1 — espaço de render compartilhado` --conceptually_related_to--> `Render HyperFrames — vídeo 'depois de assistir o filme do Tarzan'`  [INFERRED]
  scripts/README.md → log_video_tarzan5.txt
- `scene_mode = beats (padrão desde 2026-11-15)` --semantically_similar_to--> `scene_mode fica em two (§5.8)`  [AMBIGUOUS] [semantically similar]
  AGENTS.md → CONTRATO.md
- `Ambiente hardcoded (Python/Chrome/ffmpeg/CDP)` --semantically_similar_to--> `Pipeline de vídeo Videomaker v3 (10 fases)`  [INFERRED] [semantically similar]
  AGENTS.md → GUIA_REPRODUCAO.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Fases do pipeline de producao de video** — log_novo_video_fase_script, log_novo_video_fase_scenes, log_novo_video_fase_images, log_novo_video_fase_render, log_novo_video_fase_youtube [EXTRACTED 1.00]
- **Fluxo de narração TTS (primário → falha de cota → fallback)** — log_video_tarzan4_gemini_tts, log_video_tarzan4_http429_quota, log_video_tarzan4_edge_tts_fallback [EXTRACTED 1.00]
- **HyperFrames lint warnings** — log_render_bg_hyperframes_lint_check, log_render_bg_duplicate_media_discovery_risk, log_render_bg_timeline_track_too_dense, log_render_bg_nested_structure_needs_subcomposition, log_render_bg_text_below_floor, log_render_bg_container_overflow, log_render_bg_gsap_console_warning [EXTRACTED 1.00]
- **HyperFrames render execution** — log_render_bg_hyperframes_workspace_linking, log_render_bg_render_stages, log_render_bg_frame_capture_progress [EXTRACTED 1.00]
- **HyperFrames render stage with check warnings and lint tolerance** — log_video_espirrinho_google6_hyperframes_render, log_video_espirrinho_google6_hyperframes_check_warnings, log_video_espirrinho_google6_render_despite_lint, log_video_espirrinho_google6_static_frame_dedup [EXTRACTED 1.00]
- **hyperframes check lint findings** — log_novo_video7_duplicate_media_discovery_risk, log_novo_video7_timeline_track_too_dense, log_novo_video7_nested_structure_needs_subcomposition [EXTRACTED 1.00]
- **Pipeline validation gates (travas)** — log_en_trava_prompt_anti_repeticao, log_en_trava_imagens_diferentes, log_en_trava_imagens_compartilhadas [EXTRACTED 1.00]
- **Fases planejadas do pipeline de vídeo** — log_novo_video6_phase_narration, log_novo_video6_phase_timeline, log_novo_video6_phase_mix, log_novo_video6_phase_compose, log_novo_video6_phase_preprocess, log_novo_video6_phase_render [EXTRACTED 1.00]
- **Fluxo de seleção de TTS para narração** — log_novo_video6_gemini_tts, log_novo_video6_gemini_quota_failure, log_novo_video6_edge_tts_fallback [EXTRACTED 1.00]
- **Multilingual publish flow** — log_publish_all_multilingual_publish_workflow, log_publish_all_backfill_en_es, log_publish_all_pipeline_phases, log_publish_all_youtube_upload_3_langs [EXTRACTED 1.00]
- **Gemini TTS to Edge-TTS narration fallback chain** — log_video_espirrinho_google6_gemini_tts_achernar, log_video_espirrinho_google6_http_429_quota, log_video_espirrinho_google6_edge_tts_fallback [EXTRACTED 1.00]
- **Personagens Frida e Luna** — youtube_update_guide_frida, youtube_update_guide_luna, log_caminha_pt_personagens_flow [EXTRACTED 1.00]
- **Pipeline completa de geração de vídeo (10 fases)** — log_fazenda_pipeline, log_fazenda_fase_music, log_fazenda_fase_script, log_fazenda_fase_scenes, log_fazenda_fase_images, log_fazenda_fase_narration, log_fazenda_fase_timeline, log_fazenda_fase_mix, log_fazenda_fase_compose, log_fazenda_fase_preprocess, log_fazenda_fase_render [EXTRACTED 1.00]
- **Video project input artifacts** — log_novo_video7_composition_html, log_novo_video7_final_mix_m4a, log_novo_video7_bgm_gemini_wav, log_novo_video7_narration_full_wav, log_novo_video7_script_json, log_novo_video7_scenes_json, log_novo_video7_image_prompts_json, log_novo_video7_narration_timing_json, log_novo_video7_timeline_json, log_novo_video7_project_json [EXTRACTED 1.00]
- **Especificação do prompt de roteiro (Regras do Canal Frida e Luna)** — log_fazenda_err_roteiro_prompt, log_fazenda_err_regras_canal, log_fazenda_err_formato_secoes, log_fazenda_err_contrato_abertura_encerramento, log_fazenda_err_estrutura_3_atos, log_fazenda_err_formula_episodio, log_fazenda_err_elementos_obrigatorios, log_fazenda_err_luna_spec, log_fazenda_err_frida_spec [EXTRACTED 1.00]
- **Pipeline de render HyperFrames (config, lint e otimizações)** — log_video_tarzan4_hyperframes, log_video_tarzan4_render_config, log_video_tarzan4_lint_warnings, log_video_tarzan4_static_frame_dedup [EXTRACTED 1.00]
- **Sistema de fila de temas do canal** — scripts_topics_fila_oficial, scripts_topics_old_fila, scripts_topics_usados, scripts_topics_datas_especiais [INFERRED 0.70]
- **Consistência de personagens e imagens** — manual_grafos_ficha_frida_luna, manual_referencia_referencia_personagens, manual_grafos_anti_repeticao, manual_grafos_biblia_continuidade [INFERRED 0.75]
- **Fluxo de render do pipeline até publicação** — scripts_readme_pipeline_v3, scripts_readme_dez_fases, scripts_readme_render_ps1, log_video_tarzan5_render, log_video_tarzan5_hyperframes [INFERRED 0.75]
- **HyperFrames validation warnings emitted by npm run check** — log_video_gripe8_lint_warnings, log_video_gripe8_duplicate_media_discovery_risk, log_video_gripe8_timeline_track_too_dense, log_video_gripe8_nested_structure_needs_subcomposition, log_video_gripe8_text_below_floor, log_video_gripe8_container_overflow [INFERRED 0.75]
- **HyperFrames render pipeline phases** — log_en_fase_render, log_en_render_job, log_en_render_phases, log_en_fase_compose, log_en_fase_preprocess, log_en_final_mix_m4a [INFERRED 0.75]
- **Etapa de render HyperFrames** — log_es_render_hyperframes, log_es_ffmpeg, log_es_gpu_capture, log_es_static_frame_dedup, log_es_gsap_fontes [INFERRED 0.75]
- **Narrativa do video (beats de cena, gripe5)** — log_video_gripe5_introducao_video, log_video_gripe5_apresentacao_canal, log_video_gripe5_gancho_historia, log_video_gripe5_primeiro_espirro, log_video_gripe5_enfermeira_luninha, log_video_gripe5_cobertor_enrolado, log_video_gripe5_cha_mentirinha, log_video_gripe5_petiscos_medicinais, log_video_gripe5_brincadeiras_calminhas, log_video_gripe5_ronco_sarador [INFERRED 0.75]
- **Narrativa do video (beats de cena, gripe6)** — log_video_gripe6_introducao_video, log_video_gripe6_apresentacao_canal, log_video_gripe6_gancho_historia, log_video_gripe6_primeiro_espirro, log_video_gripe6_enfermeira_luninha, log_video_gripe6_cobertor_enrolado, log_video_gripe6_cha_mentirinha, log_video_gripe6_petiscos_medicinais, log_video_gripe6_brincadeiras_calminhas, log_video_gripe6_ronco_sarador, log_video_gripe6_cura_completa, log_video_gripe6_video_acabou, log_video_gripe6_agradecimento [INFERRED 0.75]
- **Video production toolchain participating in this pipeline run** — log_video_gripe7_flow_fetch, log_video_gripe7_gemini_tts_fallback_edge, log_video_gripe7_hyperframes, log_video_gripe7_ffmpeg [INFERRED 0.75]
- **Mecanismo de narracao TTS com fallback por cota** — log_novo_video4_fase_narration_gemini, log_novo_video5_gemini_tts, log_novo_video5_http429_quota, log_novo_video5_fallback_edge_tts, log_loop_completo5_edge_tts_vozes [INFERRED 0.75]
- **Pipeline de geracao do video Frida/Luna** — log_video_espirrinho_google_projeto, log_video_espirrinho_google_fases_pipeline, log_video_espirrinho_google_gemini_fetch, log_video_espirrinho_google_flow_fetch, log_video_espirrinho_google_modo_beats [INFERRED 0.75]
- **Fluxo de publicação multilíngue nos 3 canais** — configuracao_canais_youtube_tres_canais, configuracao_canais_youtube_publish_multilang, contrato_imagens_compartilhadas, log_progresso_multilang_bug_metadados, log_progresso_multilang_cota_api [INFERRED 0.75]
- **HyperFrames render pipeline execution flow** — log_render_bg_1966927817_pipeline_py, log_render_bg_1966927817_render_ps1, log_render_bg_1966927817_hyperframes_render, log_render_bg_1966927817_composition_check [INFERRED 0.75]
- **Documentações do pipeline de 11 fases** — manual_grafos_pipeline_11_fases, manual_herois_visual_liga_10_herois, manual_visual_superheroes_liga_herois [INFERRED 0.85]
- **Fluxo de render HyperFrames** — log_teste_hyperframes, log_teste_render_saida, log_teste_lint_rules, log_teste_ffmpeg [INFERRED 0.85]
- **HyperFrames render pipeline components** — log_fazenda_render_hyperframes, log_fazenda_render_render_phases, log_fazenda_render_capture, log_fazenda_render_static_dedup, log_fazenda_render_final_video [INFERRED 0.85]
- **Integrações externas de mídia da pipeline** — log_fazenda_gemini_fetch, log_fazenda_flow_fetch, log_fazenda_achernar_tts, log_fazenda_hyperframes [INFERRED 0.85]
- **Per-language EN localization flow** — log_en_traducao_gemini_web, log_en_fase_overlays, log_en_narracao_edge_tts, log_en_fase_subtitles [INFERRED 0.85]
- **Travas de validacao do pipeline** — log_es_trava_prompt_anti_repeticao, log_es_trava_imagens_repetidas, log_es_trava_imagens_compartilhadas [INFERRED 0.85]
- **Sistema de geracao de imagens (flow_fetch, banco, fallback, regras)** — log_video_gripe6_flow_fetch, log_video_gripe6_banco_de_imagens, log_video_gripe6_estrategias_fallback, log_video_gripe6_modo_imagem_nunca_video, log_video_gripe6_sem_referencia_forcada, log_video_gripe6_personagens_frida_luna [INFERRED 0.85]
- **Multilingual publish 4-step workflow** — log_loop_completo2_backfill_ok, log_loop_completo3_render_en_es, log_loop_completo3_upload, log_loop_completo3_banco_sync [INFERRED 0.85]
- **Fase de imagens do capítulo A caminha nova que ninguém quer usar** — log_caminha_pt_projeto, log_caminha_pt_flow_fetch, log_caminha_agent_lotes, log_caminha_pt_modo_imagem, log_caminha_agent_biblia [INFERRED 0.85]
- **Travas anti-repeticao e compartilhamento de imagens** — log_teste_trava_prompt_anti_repeticao, log_teste_trava_imagens_diferentes, log_teste_trava_imagens_compartilhadas, log_teste_trava_imagens_compartilhadas_render, log_teste_imagens_compartilhadas [INFERRED 0.85]
- **Pipeline de producao de video do projeto Tarzan** — log_video_tarzan_pipeline, log_video_tarzan_roteiro, log_video_tarzan_cenas, log_video_tarzan_beats, log_video_tarzan_flow_fetch, log_video_tarzan_narracao_leda, log_video_tarzan3_fases_restantes [INFERRED 0.85]
- **Fases e checkpoints do pipeline v3** — guia_reproducao_pipeline_v3, guia_reproducao_dez_fases, guia_reproducao_checkpoints, guia_reproducao_invalidacao_cascata, guia_reproducao_cli_pipeline [INFERRED 0.85]
- **HyperFrames render pipeline phases** — log_novo_video7_hyperframes_render, log_novo_video7_compile_phase, log_novo_video7_audio_process_phase, log_novo_video7_capture_screenshot, log_novo_video7_encode_phase, log_novo_video7_assemble_phase [INFERRED 0.85]
- **Script generation via Gemini WEB across retry attempts** — log_video_gripe_pipeline_script_phase, log_video_gripe_gemini_fetch, log_video_gripe_script_failure, log_video_gripe2_script_failure_retry, log_video_gripe3_script_success [INFERRED 0.85]
- **Sistema de travas anti-repetição e imagens compartilhadas** — contrato_regra_anti_repeticao, contrato_travas_repeticao, contrato_imagens_compartilhadas, log_progresso_multilang_travas, agents_checks_pre_push [INFERRED 0.85]
- **Travas anti-repetição do pipeline de imagem** — log_caminha_agent_trava_prompt, log_caminha_agent2_trava_imagens, log_caminha_pt_estrategia_suave [INFERRED 0.85]
- **Canais PT/EN/ES no fluxo de upload** — log_up_pt_upload, log_up_en_upload, log_up_es_upload [INFERRED 0.85]
- **Ordem branch → código → manual → checks → commit → push nos 3 manuais** — manual_grafos_workflow_branch_grafo_push, manual_herois_visual_ordem_sagrada, manual_visual_superheroes_ordem_sagrada [INFERRED 0.90]
- **Personagens fixas do canal (Frida e Luna)** — scripts_prompt_template_frida, scripts_prompt_template_luna, scripts_topics_frida, scripts_topics_luna [INFERRED 0.90]
- **Personagens Frida e Luna no Google Flow** — log_video_tarzan_luna, log_video_tarzan_fridoca, log_video_tarzan_personagens_flow, log_video_tarzan2_personagens_flow [INFERRED 0.90]
- **Mecanismo de checkpoint e retomada de fases** — log_video_tarzan_checkpoint, log_video_tarzan2_retomada, log_video_tarzan3_retomada [INFERRED 0.95]

## Communities (166 total, 53 thin omitted)

### Community 0 - "api.py"
Cohesion: 0.05
Nodes (50): api_create_schedule(), api_daily_agent_status(), api_daily_run(), api_daily_status(), api_daily_stop_agent(), api_daily_unpause_requeue(), api_delete_schedule(), api_get_settings() (+42 more)

### Community 1 - "gen_narration_gemini_sections.py"
Cohesion: 0.05
Nodes (41): aplicar_substituicoes_pronunciacao(), limpar_e_preparar_texto(), limpar_texto_para_tts(), load_json(), main(), gen_one(), remover_espaco_antes_pontuacao(), save_json() (+33 more)

### Community 2 - "Publishing & Image Fetch"
Cohesion: 0.05
Nodes (41): build_prompt(), install(), key_of(), load_config(), load_json(), load_state(), Lock, Log (+33 more)

### Community 3 - "Pipeline UI Upload Panel"
Cohesion: 0.08
Nodes (5): App, list_projects(), open_path(), _sh(), slugify()

### Community 4 - "description_template.py"
Cohesion: 0.24
Nodes (6): main(), _fold(), main(), _slug_tokens(), validate(), word_count()

### Community 5 - "YouTube Audit & Descriptions"
Cohesion: 0.07
Nodes (38): attach_reference(), cdp_alive(), _check_refusal(), _classify_screen(), count_dl(), default_profile(), dump_debug(), editor() (+30 more)

### Community 6 - "Daily Runner & Prompt Generation"
Cohesion: 0.06
Nodes (10): main(), main(), main(), main(), main(), main(), main(), main() (+2 more)

### Community 7 - "upload_por_idioma.py"
Cohesion: 0.20
Nodes (17): credenciais(), descricao_localizada(), enredo_localizado(), enviar_legendas(), gravar_no_projeto(), hoje(), is_done(), load_history() (+9 more)

### Community 8 - "pipeline.py"
Cohesion: 0.07
Nodes (21): cfg_ffmpeg_dir(), cmd_contract(), cmd_full(), cmd_reset(), cmd_status(), find_duplicate_by_prompt(), find_duplicate_by_slug(), find_duplicate_project() (+13 more)

### Community 9 - "limpar_duplicados_pt.py"
Cohesion: 0.19
Nodes (9): casamento_por_duracao(), extrair_duracao_local(), main(), iso_para_segundos(), list_videos(), main(), service_for(), legendas_do_video() (+1 more)

### Community 10 - "Render Log: Novo Video 7"
Cohesion: 0.06
Nodes (39): Render phase: assemble (final video 231.068s), Final audio loudness: -13.8 LUFS integrated, -1.4 dBTP true peak, Render phase: audio_process (prepare/groups/mix/master/encode/guard), bgm_gemini.wav - background music, FrameCapture: Timed out closing browser; forcing browser process shutdown, Screenshot capture mode: 6933 frames, 10 workers, captureOperation captureScreenshot, Render phase: compile (font fetches, @font-face, CDN inlining, composition metadata), Compiled composition: staticDuration 231.068s, 1920x1080, videoCount 0, audioCount 1, imageCount 41 (+31 more)

### Community 11 - "Pipeline UI Main Layout"
Cohesion: 0.11
Nodes (22): _deps_do_idioma(), fase_images(), fase_music(), fase_para_idioma(), fase_scenes(), fase_script(), garantir_legendas(), garantir_narracao() (+14 more)

### Community 12 - "Debug & Test Utilities"
Cohesion: 0.06
Nodes (33): Projeto de video: A Frida a Buldogue Brincou na Chuva, Beat: Apresentacao do canal (apresenta_o_do_canal_scene), Banco de imagens local (banco local primeiro, Flow/Gemini se nao achar), Beat: Brincadeiras calminhas (brincadeiras_calminhas_scene), Beat: Hora do cha de mentirinha (hora_do_ch_de_mentirinha_scene), Beat: O cobertor enrolado (o_cobertor_enrolado_scene), Beat: A enfermeira Luninha (a_enfermeira_luninha_scene), Fases do pipeline: images, narration, timeline, mix, compose, preprocess, render, youtube (+25 more)

### Community 13 - "Gripe Video Story Beats"
Cohesion: 0.09
Nodes (22): beat_weight(), beats_to_at(), build_prompt(), _clean_scene_text(), clean_text(), _eh_passeio(), _extrair_cenario(), fix_species() (+14 more)

### Community 14 - "json"
Cohesion: 0.13
Nodes (12): main(), load_json(), main(), probe_duration(), generate_description(), main(), load_json(), main() (+4 more)

### Community 15 - "os"
Cohesion: 0.10
Nodes (18): collect_keys(), main(), mask(), test_key(), collect_keys(), main(), mask(), test_voice() (+10 more)

### Community 16 - "Pipeline Phase Functions"
Cohesion: 0.07
Nodes (31): autoprefixer, clsx, date-fns, framer-motion, @playwright/test, postcss, tailwind-merge, tailwindcss (+23 more)

### Community 17 - "TTS Quota & Voice Checks"
Cohesion: 0.13
Nodes (13): desc(), CalendarHeader, Card, Collapsible, fnt(), labeled(), lbl(), make_field() (+5 more)

### Community 18 - "f"
Cohesion: 0.19
Nodes (9): find_project_for_title(), read_script(), f(), carregar(), main(), titulo_do_script(), improve_project_description(), load_projects() (+1 more)

### Community 19 - "Narration Alignment & Timeline"
Cohesion: 0.08
Nodes (30): bgm_gemini.wav (trilha musical reaproveitada), Capítulo Trilingue (trilingual chapter production pipeline), HeadlessChrome 152.0.7977.30 (screenshot capture, GPU ANGLE/D3D11), composition.html (17939 bytes, composição linkada ao index.html), Compiled composition metadata (1920x1080, 30fps, 186.993s, 22 imagens, 1 áudio), FASE compose[en] (composition.html, total 186.993 s), FASE images (21 imagens reaproveitadas), FASE mix[en] (final_mix.m4a; -14.0 LUFS; -1.2 dBTP) (+22 more)

### Community 20 - "Pipeline UI Scheduler"
Cohesion: 0.09
Nodes (27): Log de teste: CAPITULO TRILINGUE, Fases do pipeline (script, scenes, images, music, overlays, narracao, legendas, timeline, mix, compose, preprocess, render, traducao), FFmpeg (C:\videomaker\ffmpeg\bin), Gemini WEB — tradução de texto (TRADUCAO[en]), HyperFrames 0.8.225 (npm run check / npm run render --workers 10), Regras de lint do HyperFrames (duplicate_media_discovery_risk, timeline_track_too_dense, nested_structure_needs_subcomposition, text_below_floor), Mix de áudio final_mix.m4a (-14.0 LUFS / -1.3 dBTP), Pipeline CAPITULO TRILINGUE (gerar_capitulo_trilinguo.py) (+19 more)

### Community 21 - "EN Production Log Concepts"
Cohesion: 0.06
Nodes (30): Ambiente hardcoded (Python/Chrome/ffmpeg/CDP), Só um render por vez (ffmpeg não thread-safe), publish_multilang.py (orquestra upload por idioma), youtube_captions.py (envia legendas .srt), youtube_upload.py (upload real para o YouTube), Duração mínima do vídeo e áudio — REGRA DE OURO (§5.12), Estratégia disco rápido C: + histórico lento E: (§5.5), Frase do coração (narration_contract.py) (+22 more)

### Community 22 - "Character Audit & Translation"
Cohesion: 0.09
Nodes (27): Gemini TTS 'Achernar' (gemini-3.8-flash-tts), pipeline.py: error: unrecognized arguments — prompt repassado como CLI, CONTRATO DE ABERTURA E ENCERRAMENTO (REGRA CRÍTICA), ELEMENTOS OBRIGATORIOS DESTE EPISODIO (fazenda, animais, culinária mineira), ESTRUTURA EM 3 ATOS (gancho, desenvolvimento, clímax/lição/CTA), Fórmula de cada episódio (s0, gancho, promessa, desenvolvimento, clímax, final, s_outro), Frida — especificação de personagem (buldogue inglesa, tranquila, gulosa), Luna — especificação de personagem (salsicha fêmea, briguenta, chefona) (+19 more)

### Community 23 - "Test & Upload Logs"
Cohesion: 0.07
Nodes (22): Anti-duplicação de narração (faster-whisper) e frase do coração, Capa (intro-capa) sem transição inicial, Capítulo trilíngue (gerar_capitulo_trilinguo.py), Chips de palavras-chave desativados por padrão, Padrão oficial de descrição (description_template.py), Gemini TTS (Achernar/Leda) e rotação de chaves, O manual é a memória do produto, Narração multi-idioma e legendas (pt/en/es) (+14 more)

### Community 24 - "flow_agent_batch.py"
Cohesion: 0.19
Nodes (9): _biblia_do_prompt(), _cena_do_prompt(), get_page(), _hash_imagem(), _hashes_existentes(), main(), main_async(), processar_lote() (+1 more)

### Community 25 - "Fazenda Pipeline Log"
Cohesion: 0.16
Nodes (29): ActionBar(), AppShell(), DURATION_PRESETS, iso(), PAGE_TITLES, PageActivity(), PageCreate(), PageDaily() (+21 more)

### Community 26 - "Manual de Grafos Concepts"
Cohesion: 0.08
Nodes (24): Audio mix of narration + BGM with loudness normalization (Input Integrated -13.9 LUFS, True Peak -1.4 dBTP), flow_fetch r2-2026-11-07 - Google Flow image generation via CDP + Playwright + Gemini TTS, Gemini TTS narration voice 'Achernar' using gemini-3.8-flash-tts and gemini-3.8-flash-lite-tts, Google Flow 'modo Imagem' (x1, 16:9) generates static images, never video; characters Frida e Luna injected via prompt, HTTP 429 daily quota exhaustion forcing model switch from flash-tts to flash-lite-tts and retries, HyperFrames check/lint warnings: duplicate_media_discovery_risk, timeline_track_too_dense, nested_structure_needs_subcomposition, container_overflow, text_below_floor, GSAP console_warning, HyperFrames render via npm (hyperframes@0.8.225, --workers 10, 30fps, 1920x1080, AMD/ANGLE d3d11 GPU), network_fallback image download with strategies original, suave, simplificada, generica; retries when Flow stalls (+16 more)

### Community 27 - "Project"
Cohesion: 0.08
Nodes (13): phase_compose(), phase_mix(), phase_narration(), run_edge(), run_gemini(), phase_preprocess(), phase_render(), phase_scenes() (+5 more)

### Community 28 - "TTS Fallback & Audio Mix Logs"
Cohesion: 0.10
Nodes (24): Global banks sync (images and music), HTML composition (index.html / composition.html), container_overflow layout info (22 instances), projects-deliveries.json (delivery record), duplicate_media_discovery_risk lint warning, FFmpeg media metadata tooling (on PATH), final_mix.m4a audio track (-13.9 LUFS, -1.2 dBTP), GSAP target not found runtime console warnings (4) (+16 more)

### Community 29 - "flow_mcp.py"
Cohesion: 0.16
Nodes (6): _log(), main(), MCPServer, _run_flow_fetch(), _sanitize_filename(), _validate_prompt()

### Community 30 - "Flow Fetch / Inspect Agent Mode2"
Cohesion: 0.10
Nodes (22): Estrategia suave apos falha de download direto da tela, flow_fetch.py r2-2026-11-07 gerando as imagens restantes, Personagens Frida e Luna no Flow, referencia forcada: nenhuma, Fases restantes apos images: narration, timeline, mix, compose, preprocess, render, Fase narration: Gemini TTS 'Leda' (Google AI Studio), Artefatos do projeto (script.json, scenes.json, image_prompts.json, narration_timing.json, timeline.json, final_mix.m4a, composition.html), Banco de imagens local (C:\videomaker\banco de imagens), Trilha do banco local de musicas (+14 more)

### Community 31 - "publish_multilang.py"
Cohesion: 0.15
Nodes (17): build_description_i18n(), get_credentials(), get_storyline(), get_title_lang(), get_title_pt(), is_project_done(), load_history(), load_json() (+9 more)

### Community 32 - "build_description"
Cohesion: 0.15
Nodes (8): build_description(), _clean_sentence(), description_for_project(), extract_storyline(), _fit_storyline(), main(), to_utc_iso(), upload()

### Community 33 - "Limpar Duplicados Pt / Listar Canal"
Cohesion: 0.14
Nodes (13): add_schedule(), done_phases(), enable_dpi(), fmt_dur(), load_schedules(), load_state(), load_state_daily(), main() (+5 more)

### Community 34 - "Es"
Cohesion: 0.08
Nodes (23): Banco de imagens/musicas global sync, HyperFrames render (10 workers, 888.5s/674.4s), Successful multilingual publish retry (backfill-render-upload), Thumbnail upload a_li_o_do_dia_scene.jpg (PT/EN/ES), Edge-TTS EN narration (en-US-AriaNeural, 222.1s), Project: frida-e-luna-fazenda-minas-gerais, publish_multilang.py render_lang (--skip-check), Publish run resume (skip already-processed projects) (+15 more)

### Community 35 - "Loop40"
Cohesion: 0.11
Nodes (23): Capitulo Trilingue (Trilingual Chapter) build, Composicao HTML (composition.html), FFmpeg (C:\videomaker\ffmpeg\bin), Captura screenshot com GPU por hardware (Chrome headless), Animacoes GSAP e fontes (Roboto, Inter, EB Garamond), 21 imagens compartilhadas por PT/EN/ES, Normalizacao de loudness (-14.0 LUFS / -1.0 dBTP), Mixagem de audio (final_mix.m4a) (+15 more)

### Community 36 - "youtube_metadados.py"
Cohesion: 0.24
Nodes (8): listar_todos_videos(), main(), apagar(), atualizar(), carregar_metadados(), get_service(), main(), get_service()

### Community 37 - "criar_efeitos_final.py"
Cohesion: 0.11
Nodes (5): build_cmd(), estrela(), main(), overlays(), estrela()

### Community 38 - "Contrato / Agents"
Cohesion: 0.15
Nodes (7): fit_text(), mix(), NavItem, PhaseChip, rr(), StatusPill, Switch

### Community 39 - "Flow Fetch"
Cohesion: 0.10
Nodes (22): Render input artifacts — script.json, scenes.json, image_prompts.json, narration_timing.json, timeline.json, bgm_gemini.wav, final_mix.m4a, composition.html, Audio normalization — -14.7 LUFS, -1.8 dBTP, lowered 0.8 dB, Global banks sync after render (1 music copied), Screenshot capture — 10 headless Chrome workers @ 30fps, hardware GPU, project-control.json + projects-deliveries.json records, Final MP4 — 257.47s, 274.4MB, h264 1920x1080@30fps, AAC, GSAP animations — #outro-final targets warned missing, HyperFrames v0.8.225 render engine (npx hyperframes render --workers 10) (+14 more)

### Community 40 - "Novo Video / Loop Completo5"
Cohesion: 0.12
Nodes (17): Checks obrigatórios antes do push, flow_fetch.py (Google Flow), Imagem gerada somente pelo Google Flow, Imagens geradas uma vez em PT e compartilhadas PT/EN/ES, Vídeo NÃO é conteúdo para crianças, Auditoria de personagens nas imagens (§5.13), Consistência de cenário, personagens e lição educativa (§5.1), Imagens compartilhadas entre PT/EN/ES (§5.9) (+9 more)

### Community 41 - "criar_efeitos_final_v2.py"
Cohesion: 0.12
Nodes (3): build_cmd(), fumaca_organica(), main()

### Community 42 - "Youtube Metadados / Youtube Upload"
Cohesion: 0.11
Nodes (19): project-control.json e projects-deliveries.json (controle e entrega), Falha de upload de legendas (HttpError 403 - escopo de autenticacao insuficiente), Sincronizacao dos bancos globais de imagens e musicas, Upload para o YouTube, Copia de imagens geradas para o banco de imagens global, Estrategias de retry do flow_fetch: original / suave / simplificada / generica, Fase images: geracao de imagens (banco local primeiro, Flow/Gemini depois), Fase render: renderizacao do video via HyperFrames (+11 more)

### Community 43 - "Topics-Old / Topics"
Cohesion: 0.14
Nodes (19): final_mix.m4a (narração + trilha, -13.8 LUFS, -1.4 dBTP), Google Fonts (Roboto, Inter, EB Garamond) injetadas via @font-face deterministic, Gemini TTS HTTP 429 / cota diária esgotada (10 seções falharam), Gemini TTS (Google AI Studio, voz Achernar), GSAP 3.15.0 (animações; targets #outro-final .body não encontrados), HyperFrames (npx hyperframes@0.8.225) — motor de composição/render, HyperFrames check (lint/validação antes do render), HyperFrames render (30fps, 10 workers, screenshot capture, 1920x1080, 6933 frames) (+11 more)

### Community 44 - "Pipeline Ui-Old"
Cohesion: 0.11
Nodes (19): Lista de publicação — vídeos prontos para upload EN/ES, Frida — bulldog inglesa ranzinza e dorminhoca, Luna — salsicha esperta e curiosa, Template de roteiro de episódio animado, check_topico_novo.py — checagem de duplicidade, Datas especiais (@MM-DD), Fila oficial de 365 temas de vídeo novo, Frida — Bulldogue Inglês (+11 more)

### Community 45 - "re"
Cohesion: 0.17
Nodes (10): main(), chips_from(), clean(), esc(), first_sentence(), is_intro_section(), load_json(), main() (+2 more)

### Community 46 - "gen_narration_voicecraft.py"
Cohesion: 0.19
Nodes (7): limpar(), main(), gen_one(), synthesize(), api_up(), main(), synthesize()

### Community 47 - "Flow Fetch"
Cohesion: 0.16
Nodes (18): Pipeline abortado pela trava de imagens repetidas, Trava: imagens diferentes entre si (check_imagens_repetidas), Regeneração parcial de imagens duplicadas (8 pendentes), Bíblia de personagens encontrada, Geração de imagens em lotes via modo Agente do Flow, Trava: prompt anti-repetição (check_prompt_repeticao), Estratégia 'suave' de retry ao descartar imagem repetida, flow_fetch r2-2026-11-07 (Google Flow via CDP + Playwright + Gemini TTS) (+10 more)

### Community 48 - "Youtube Update Guide / Caminha Pt"
Cohesion: 0.17
Nodes (13): lucide-react, LiveStrip(), PipelineRail(), isLive(), LogsCtx, PHASE_KEYS, phaseLabel(), RunBusProvider() (+5 more)

### Community 49 - "Userunbus / Phases"
Cohesion: 0.18
Nodes (12): autofill(), build_master_prompt(), build_script_brief(), channel_style(), detect_pipeline(), duration_to_seconds(), episode_params(), _fill() (+4 more)

### Community 50 - "gen_music_procedural.py"
Cohesion: 0.23
Nodes (9): add(), bass(), env_ad(), main(), marimba(), pluck(), section(), shaker() (+1 more)

### Community 51 - "Prompt Gen - Copia"
Cohesion: 0.13
Nodes (15): Pulo de imagens ja existentes (ja existe) em retomadas do pipeline, Falha de todas as estrategias (48s cada) e retry 1/1 em a_sesta_curativa_scene_d, Falha de todas as estrategias (48s cada) e retry 1/1 em o_v_deo_acabou_scene_b, Banco de imagens local (copia das imagens geradas), Checkpoint de fase (music feito em 2026-11-09 18:03:09, pulando), Estrategias de download: original, suave, simplificada, generica (network_fallback), Fases do pipeline: script, scenes, music, images, narration, timeline, mix, compose, preprocess, render, youtube, flow_fetch.py r2-2026-11-07 - Google Flow via CDP + Playwright + Gemini TTS (+7 more)

### Community 52 - "subprocess"
Cohesion: 0.10
Nodes (13): main(), main(), main(), duracao(), gerar_frase(), main(), batch_rodando(), log() (+5 more)

### Community 54 - "match_videos_by_duration.py"
Cohesion: 0.27
Nodes (8): _tokens(), ffprobe_duration(), get_service(), list_channel_videos(), main(), parse_iso_duration(), project_video_path(), title_score()

### Community 55 - "rerender_all_no_text.py"
Cohesion: 0.27
Nodes (6): get_final_videos(), load_json(), main(), regenerate_scene_htmls(), reset_phases(), run_pipeline()

### Community 56 - "Build Composition / Mix Audio"
Cohesion: 0.21
Nodes (8): build(), collect_anims(), inject_ids(), load_json(), _load_paineis(), main(), _txt(), _video_clips_config()

### Community 59 - "Youtube Batch Publish"
Cohesion: 0.21
Nodes (7): build_description(), build_tags(), find_thumbnail(), get_final_videos(), get_title_and_prompt(), load_json(), main()

### Community 60 - "Loop Completo2 / Loop Completo"
Cohesion: 0.17
Nodes (13): Backfill concluido — EN/ES translation, narration, subtitles, pipeline.py cmd_full — planned phases (narration/subtitles/timeline/mix/compose/preprocess/render), execute_phases() → phase_narration() call chain, render_lang() — re-render a language via pipeline.py, FileNotFoundError — artifacts/script.json missing (fase script), Subtitle .srt generation (8 blocos), translate_script()/load_json() — roteiro translation to EN/ES, Backfill de idiomas EN e ES (publish step 1/4) (+5 more)

### Community 61 - "Render Bg 1966927817 / Render Bg Err"
Cohesion: 0.19
Nodes (9): FFmpeg (C:\videomaker\ffmpeg\bin), HyperFrames render engine (hyperframes@0.8.225), scripts/pipeline.py render call chain, Video project a-frida-espirrinho-luninha-cuida, scripts/render.ps1, Static-frame dedup optimization, Frame capture progress with 10 workers, HyperFrames render engine job 7ce565a2 (in progress) (+1 more)

### Community 62 - "generate_thumbnail.py"
Cohesion: 0.53
Nodes (4): draw_text_with_outline(), generate_thumbnail(), load_font(), main()

### Community 63 - "atualizar_endscreen.py"
Cohesion: 0.22
Nodes (6): esperar_login(), listar_videos_shadow(), main(), navegar_videos(), processar_video(), shadow_click()

### Community 65 - "loop40.py"
Cohesion: 0.18
Nodes (15): audit(), build_cmd(), build_reserved_index(), extract_titles(), is_reserved(), load_deliveries(), load_json_file(), main() (+7 more)

### Community 66 - "test_paineis.py"
Cohesion: 0.32
Nodes (4): montar_prompt_lote(), check(), img_bytes(), main()

### Community 67 - "translate_script.py"
Cohesion: 0.24
Nodes (8): load_json(), main(), normalizar_apelidos(), parece_recusa(), remover_risadas(), save_json(), translate_script(), translate_text()

### Community 68 - "Translate Script"
Cohesion: 0.18
Nodes (10): Pipeline phases: images, narration, timeline, mix, compose, preprocess, render (optional youtube), FFmpeg on PATH (C:\videomaker\ffmpeg\bin) used by HyperFrames render, Google Flow image generation - flow_fetch r2-2026-11-07 via CDP + Playwright (mode Imagem x1 16:9, nunca video), Google Fonts fetched for composition: Roboto, Inter, EB Garamond, GSAP animation library in composition (emits target-not-found warnings), HyperFrames render engine v0.8.225 (30fps, 10 workers, screenshot capture, hardware GPU), HyperFrames layout/craft/runtime checks: container_overflow, text_below_floor, GSAP target-not-found console warnings, HyperFrames lint/check diagnostics: duplicate_media_discovery_risk, timeline_track_too_dense, nested_structure_needs_subcomposition (+2 more)

### Community 69 - "Video Gripe7"
Cohesion: 0.18
Nodes (10): Banco de imagens e músicas locais (BM25 / FTS5), Bíblia de Continuidade (continuity_notes), daily_runner.py + prompt_gen.py (brief Frida e Luna), Ordem de busca de imagens: banco local → Flow → Gemini, Ficha canônica de Frida e Luna (fonte única de verdade), Fila de temas (scripts/topics.txt), Google Flow (flow_fetch.py) e servidor MCP (flow_mcp.py), Música procedural (fallback sem API) (+2 more)

### Community 70 - "Manual Grafos / Manual Referencia"
Cohesion: 0.27
Nodes (5): buscar_imagem_no_banco(), extrair_palavras_chave(), listar_imagens_disponiveis(), main(), normalizar_texto()

### Community 71 - "flow_fetch.py"
Cohesion: 0.05
Nodes (49): attach_reference(), _bytes_igual_ref(), cdp_alive(), _classify_screen(), _copiar_para_banco(), count_dl(), default_profile(), _dismiss_overlays() (+41 more)

### Community 72 - "Match Videos By Duration"
Cohesion: 0.18
Nodes (6): react, react-dom, react@^18.3.1, react-dom@^18.3.1, App(), KpiTile()

### Community 73 - "gen_subtitles.py"
Cohesion: 0.36
Nodes (5): fmt_srt(), gerar_srt(), limpar_legenda(), load_json(), main()

### Community 75 - "canal_match.py"
Cohesion: 0.21
Nodes (8): casar_por_duracao(), duracao_mp4(), _fold(), mapa_de_videos(), melhor_projeto(), norm(), perfis_projetos(), tokens()

### Community 76 - "check_video_idioma.py"
Cohesion: 0.21
Nodes (7): _comparar(), main(), _manifesto(), check_project(), main(), sha256(), sidecar_lang()

### Community 77 - "Video Tarzan5 / Readme"
Cohesion: 0.24
Nodes (10): Mixagem de áudio final (final_mix.m4a, -13.8 LUFS, -1.4 dBTP), Fallback Edge-TTS (pt-BR-ThalitaNeural, local sem API), Gemini TTS (voz Achernar) — provedor primário de narração, HTTP 429 — cota diária esgotada (gemini-3.8-flash-tts / flash-lite-tts), HyperFrames — composição e renderização do vídeo, Avisos de lint do HyperFrames check (duplicate_media_discovery_risk, timeline_track_too_dense, nested_structure_needs_subcomposition, text_below_floor, container_overflow, GSAP target not found), Fases do pipeline: narration, timeline, mix, compose, preprocess, render, youtube, Configuração de render: 30fps, 10 workers, modo screenshot, GPU AMD Radeon, 5388 frames (+2 more)

### Community 78 - "Youtube Captions"
Cohesion: 0.24
Nodes (10): Sincronização de bancos de imagens e músicas, FFmpeg — PATH de codificação de vídeo, HyperFrames — compiler/render engine (npx 0.8.225), Render HyperFrames — vídeo 'depois de assistir o filme do Tarzan', Publicação YouTube — KH6GWZBepr0, Fases do pipeline (ordem fixa de 10 fases), narration_contract.py — contrato de abertura/encerramento, Pipeline Videomaker v3 (orquestrador) (+2 more)

### Community 79 - "shutil"
Cohesion: 0.26
Nodes (8): has_file(), main(), missing_for_lang(), process_lang(), processo_projeto(), run(), load_json(), main()

### Community 80 - "fetch_images.py"
Cohesion: 0.22
Nodes (8): clean_prompt_text(), copy_to_bank(), _garantir_modo_imagem(), get_ref_image(), load_json(), main(), run_single(), sanitize_prompts_file()

### Community 81 - "atualizar_endscreen_playwright.py"
Cohesion: 0.22
Nodes (6): js_click_texto(), js_existe_texto(), listar_videos_pagina(), main(), navegar_conteudo(), processar_video_endscreen()

### Community 82 - "time"
Cohesion: 0.09
Nodes (17): dismiss_ads_and_permissions(), fetch_url(), main(), main(), main(), baixar(), conectar(), enviar() (+9 more)

### Community 83 - "Gen Subtitles"
Cohesion: 0.22
Nodes (9): Auditoria do YouTube Publishing (2025-11-06), Projeto caes-de-resgate com título e descrição vazios, Novo padrão de descrição do YouTube, Scripts de padronização de descrições, Credenciais OAuth2 por idioma (client_secret_*.json + youtube_token_*.json), Erro 403 insufficientPermissions (escopo youtube.force-ssl), 3 canais separados do YouTube (PT/EN/ES), Metadado do YouTube no idioma do vídeo (§5.7) (+1 more)

### Community 84 - "_enviar_uma_vez"
Cohesion: 0.18
Nodes (5): ativar_agente(), baixar_novas(), dividir_colagem(), _enviar_uma_vez(), open_image_page()

### Community 85 - "check_personagens_imagens.py"
Cohesion: 0.29
Nodes (3): auditar(), extract_json(), main()

### Community 86 - "check_texto_idioma.py"
Cohesion: 0.46
Nodes (5): checar_overlay(), checar_script(), load(), main(), norm()

### Community 87 - "detecta_paineis.py"
Cohesion: 0.48
Nodes (3): main(), n_paineis(), _score_line()

### Community 88 - "check_prompt_repeticao.py"
Cohesion: 0.33
Nodes (6): _checar_build_prompt(), _checar_scene_mode(), main(), normalizar(), _varrer_fonte(), _varrer_prompts()

### Community 90 - "os"
Cohesion: 0.09
Nodes (22): main(), has_file(), main(), missing_for_lang(), process_lang(), run(), compose(), has_file() (+14 more)

### Community 91 - "Relatorio Youtube Idiomas"
Cohesion: 0.32
Nodes (4): build_description(), build_tags(), load_json(), main()

### Community 92 - "Backfill Languages"
Cohesion: 0.50
Nodes (6): PageExecutivo(), LogHistogram(), PhaseGauge(), Sparkline(), Waterfall(), fmtDuration()

### Community 93 - "unicodedata"
Cohesion: 0.36
Nodes (5): coverage(), load_audio(), load_json(), main(), norm()

### Community 94 - "Pipeline"
Cohesion: 0.29
Nodes (6): Backfill de idiomas EN e ES, Vozes Edge-TTS por idioma (en-US-AriaNeural, es-ES-ElviraNeural), Re-render em ingles e espanhol, Fase narration: Gemini TTS 'Achernar' (Google AI Studio), Gemini TTS (Google AI Studio) - vozes Achernar e Leda, HTTP 429: cota diaria esgotada nos modelos Gemini TTS

### Community 95 - "audit_youtube.py"
Cohesion: 0.22
Nodes (6): build_rich_description(), enrich_tags(), get_service(), list_uploads(), main(), st_flag()

### Community 96 - "Contrato / Agents"
Cohesion: 0.33
Nodes (6): Projetos sem script.json (não traduzíveis nem publicáveis), Status geral dos projetos por idioma (2026-11-12), Título em português na capa dos MP4s antigos, Cota da YouTube Data API (~6 uploads por canal por dia), scripts/loop_upload_idiomas.py, Status de publicação por idioma (PT 33/46, EN 6/49, ES 5/49)

### Community 97 - "install_hooks.py"
Cohesion: 0.48
Nodes (4): _git(), instalar(), main(), status()

### Community 98 - "execute_phases"
Cohesion: 0.15
Nodes (4): execute_phases(), invalidate_downstream(), walk(), _validate_prereq()

### Community 100 - "Make Contact Sheet"
Cohesion: 0.50
Nodes (5): API do backend (FastAPI) e endpoints REST/WebSocket, RunBus / LiveStrip / observabilidade, Interface Web Premium (React + FastAPI + Vite), Nave Espacial — UI Web (React + FastAPI), Nave Espacial — UI Web (React + FastAPI)

### Community 101 - "Pipeline Ui"
Cohesion: 0.40
Nodes (3): config.json campo reference_image, fetch_images.py passa --ref-image ao gemini_fetch.py, setup_reference_image.py

### Community 104 - "Manual Usuario"
Cohesion: 0.50
Nodes (3): Render CHECKPOINT skip (2026-11-09), Project: luna-a-salsicha-fica-com-medo-de-trovao, YouTube publication (kids=True, public, pt-BR)

### Community 105 - "Pipeline"
Cohesion: 0.50
Nodes (3): Roteiro longo (18 seções) e densidade de imagens, scene_mode = beats (uma imagem por beat de narração), Transições e animações por beat (build_composition.py)

### Community 106 - "Probe Edge Voices"
Cohesion: 0.50
Nodes (4): Agendar automático (calendário), Fluxo básico: gerar um vídeo, Páginas da interface web, Sistema de vídeos animados Frida e Luna

### Community 107 - "align_narration.py"
Cohesion: 0.36
Nodes (7): cut(), find_section(), load_audio(), load_json(), main(), norm(), transcribe_words()

### Community 108 - "phase_music"
Cohesion: 0.33
Nodes (3): carregar_controle_musicas(), _music_prompt(), phase_music()

### Community 109 - "Manual Grafos / Manual Herois Visual"
Cohesion: 0.67
Nodes (3): Frame capture progress (6912 frames, 30fps, 10 workers), composition.html + final_mix.m4a linked to hyperframes-workspace, HyperFrames render stages (compile-extract_video-process_audio-start_browsers-capture)

### Community 110 - "Readme"
Cohesion: 1.00
Nodes (3): Interface Tkinter (pipeline_ui.py), Quartel General Móvel — Pipeline UI (Tkinter), Quartel General Móvel — Pipeline UI (Tkinter)

### Community 146 - "check_imagens_repetidas.py"
Cohesion: 0.48
Nodes (4): _assinatura(), conferir_projeto(), _distancia(), main()

### Community 147 - "gen_narration.py"
Cohesion: 0.53
Nodes (4): ffprobe_duration(), load_json(), main(), synthesize()

### Community 148 - "select_topic.py"
Cohesion: 0.23
Nodes (8): main(), espalhados(), load_topics(), main(), normalize(), parecidos(), slugify(), temas_novos()

### Community 149 - "diag_modelo.py"
Cohesion: 0.29
Nodes (3): main(), main(), _loc_first_visible()

### Community 153 - "youtube_captions.py"
Cohesion: 0.31
Nodes (6): get_service(), insert_caption(), list_captions(), load_json(), main(), save_json()

### Community 156 - "phase_images"
Cohesion: 0.17
Nodes (7): buscar_imagem_banco(), copiar_para_projeto(), extrair_palavras_chave(), normalizar_texto_local(), phase_images(), run_single_fetch(), tentar()

### Community 157 - "sync_bancos.py"
Cohesion: 0.36
Nodes (3): copy_if_missing(), main(), sync_project()

### Community 159 - "argparse"
Cohesion: 0.11
Nodes (12): backfill_project(), load_json(), main(), run(), extrair_cena(), main(), load_json(), main() (+4 more)

### Community 160 - "criar_efeitos_teste_v2.py"
Cohesion: 0.60
Nodes (3): bolha(), filtro(), main()

### Community 161 - "pathlib"
Cohesion: 0.14
Nodes (7): gen(), main(), gen(), main(), get_service(), main(), update_video()

### Community 162 - "_gemini_tts_key"
Cohesion: 0.40
Nodes (3): _gemini_tts_key(), generate_audio_gemini(), _read_env_value()

## Ambiguous Edges - Review These
- `scene_mode = beats (padrão desde 2026-11-15)` → `scene_mode fica em two (§5.8)`  [AMBIGUOUS]
  AGENTS.md · relation: semantically_similar_to
- `Narração com emoção (§5.14)` → `Regras de qualidade da narração (sem SSML, sem risadas escritas)`  [AMBIGUOUS]
  GUIA_REPRODUCAO.md · relation: semantically_similar_to

## Knowledge Gaps
- **231 isolated node(s):** `Render phase: assemble (final video 231.068s)`, `bgm_gemini.wav - background music`, `FrameCapture: Timed out closing browser; forcing browser process shutdown`, `Render phase: encode (framesFed 6799/6933)`, `FFmpeg on PATH at C:\videomaker\ffmpeg\bin` (+226 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 871 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `Pipeline UI Upload Panel` to `Limpar Duplicados Pt / Listar Canal`, `Contrato / Agents`, `.__init__`, `TTS Quota & Voice Checks`, `Video Espirrinho Google`, `.cal_add_schedule`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `Render phase: assemble (final video 231.068s)`, `bgm_gemini.wav - background music`, `FrameCapture: Timed out closing browser; forcing browser process shutdown` to the rest of the system?**
  _231 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `api.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05030834144758196 - nodes in this community are weakly interconnected._
- **Why does `Project` connect `Project` to `.__init__`, `execute_phases`, `pipeline.py`, `phase_music`, `phase_images`, `phase_youtube`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Should `gen_narration_gemini_sections.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0518326545723806 - nodes in this community are weakly interconnected._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `scene_mode = beats (padrão desde 2026-11-15)` and `scene_mode fica em two (§5.8)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **What is the exact relationship between `Narração com emoção (§5.14)` and `Regras de qualidade da narração (sem SSML, sem risadas escritas)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._