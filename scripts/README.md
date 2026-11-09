# Scripts do pipeline Videomaker v3

Referência rápida do que cada script faz. O manual completo (com exemplos, config e troubleshooting) está no `GUIA_REPRODUCAO.md` da raiz.

Projeto raiz: `C:\videomaker\hyperframes-workspace`
Cada prompt gera um projeto em `projects/<slug>/` com checkpoints (`project.json`).

## Orquestrador

```powershell
python scripts/pipeline.py full   --prompt "Vídeo educativo sobre banho em cachorro"   # novo projeto, 10 fases
python scripts/pipeline.py resume --slug video-educativo-sobre-banho-em-cachorro --no-parallel --duration 590  # retomar
python scripts/pipeline.py status --slug video-educativo-sobre-banho-em-cachorro        # auditoria dos checkpoints
python scripts/pipeline.py reset  --slug video-educativo-... --phase narration            # reset (cascata das dependentes)

python scripts/pipeline_ui.py -p "Vídeo educativo sobre..."                              # UI tkinter
```

Fases (ordem fixa): `script → scenes → images → music → narration → timeline → mix → compose → preprocess → render`.
- `full`/`resume`: `--from <fase>|auto`, `--only p1,p2`, `--skip p1,p2`, `--force`, `--no-parallel`, `--duration <s>`.
- Narração: `--voice pt-BR-ThalitaNeural --rate +12% --pitch +8Hz` (`--style` ignorado).
- IA web: `--wait 240 --pause 8` (timeout/pausa do scraping do Gemini).
- `--provider procedural`: trilha offline em vez do Gemini.

## Scripts por fase

| Fase | Script | IA |
|------|--------|----|
| script | `generate_script_from_prompt.py` | Gemini web (texto) |
| scenes | `generate_scenes_and_prompts.py` → `generate_scene_htmls.py` | local |
| images | `fetch_images.py` | Gemini web (imagens) |
| music | `fetch_music_gemini.py` (fallback: `gen_music_procedural.py`) | Gemini web (áudio) |
| narration | `gen_narration_edge.py` | **local** (Edge-TTS) |
| timeline | `build_timeline.py` | local |
| mix | `mix_audio.py` | local |
| compose | `build_composition.py` | local |
| preprocess | `preprocess_images.py` | local |
| render | `render.ps1` + `verify_output.py` | local |

Todos os scripts por fase aceitam `--proj <pasta-do-projeto>`; o render recebe `-ProjectDir/-Slug/-CompFile/-MixFile`.

## Regras importantes

- **Contrato de abertura/encerramento** (`narration_contract.py`): garante a ordem `s_intro` (gancho) → `s0` (saudação variada) → conteúdo → `s_final` (aviso de fim) → `s_outro` (agradecimento/CTA variável). Os textos não são fixos: saudação, aviso de fim e agradecimento variam a cada vídeo para não soar robótico. Aplicado na fase `script` e na `narration`; validado no checkpoint `script`.
- **`gemini_fetch.py` nunca pede vídeo**: material visual é sempre `--kind image` (imagem estática única). `--kind video` é recusado e todo prompt de imagem recebe o reforço `IMAGE_ONLY_PREFIX` (anti-vídeo).
- **Narração = texto puro, sem SSML** (SSML é lido em voz alta) e **sem risadas escritas** ("Hahaha!" é removido por `LAUGH_RE` — soa falsa em voz neural).
- **Invalidação em cascata**: reset na fase X caduca as fases dependentes; `full` re-executa só o necessário.
- **Espaço de render compartilhado**: `render.ps1` copia `composition.html` e `final_mix.m4a` do projeto para `hyperframes-workspace/` antes de renderizar — um projeto por vez.
- IA web (script/images/music) requer Chrome logado no Gemini: `gemini_fetch.py --check` (exit 3 = Chrome fora da CDP 18800; exit 4 = login expirado).

## Upload YouTube

```powershell
python scripts/youtube_upload.py --video projects/<slug>/output/<slug>.mp4 `
    --title "Título do vídeo" `
    --description "Descrição completa" `
    --tags "cachorro,animacao,infantil" `
    --privacy public `
    --made-for-kids `
    --thumbnail "caminho/para/thumb.jpg" `
    --default-language pt-BR `
    --default-audio-language pt-BR
```

Quando chamado via `pipeline.py full --publish`, a descrição é gerada automaticamente
contendo: título, tema, marcação "Vídeo gerado por inteligência artificial (IA)",
"Not contains paid promotion", idioma "Português do Brasil", "Conteúdo infantil"
e hashtags. A thumbnail usa `--yt-thumb` se informado, senão a primeira imagem da
cena do projeto. O idioma padrão é `pt-BR` para vídeo e áudio.

## Utilitários (fora do pipeline)

| Script | Uso |
|--------|-----|
| `gemini_fetch.py` | scraping direto do Gemini (imagem/texto/áudio/vídeo); `--login`, `--check` |
| `make_contact_sheet.py` | grade de frames do MP4 final (QA visual) |
| `verify_narration.py` | transcreve a narração e compara com o roteiro |
| `probe_tts.py` | diagnóstico de chave/modelos de TTS (legado Gemini TTS) |
| `align_narration.py` / `gen_narration.py` / `gen_narration_gemini.py` | fluxo antigo; substituídos por `gen_narration_edge.py` |
