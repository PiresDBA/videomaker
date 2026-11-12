# LOG DE PROGRESSO — Reprocessamento multilíngue (pt → en/es)

> Este log é atualizado a cada execução do loop. Qualquer agente que pegar o
> trabalho deve ler este arquivo antes de começar para saber onde parou.

## Estratégia de trabalho

- **Disco de trabalho (rápido):** `C:\videomaker\projects` (SSD).
- **Disco histórico (lento):** `E:\videomaker\projects` (arquivo de verdade).
- **Fluxo por projeto:**
  1. Copiar de E: para C:\videomaker\projects\
  2. Processar en/es em C: (tradução local, narração com fallback Edge-TTS,
     timeline, mix, composição, render).
  3. Copiar de volta para E: (sobreescreve o histórico).
  4. Registrar na LISTA_PUBLICACAO.md os projetos com en/es completos.

## Scripts
- `scripts/loop_publicacao.py` — loop completo com lista de publicação.
- `scripts/translate_local.py` — tradução local pt→en/es.
- `scripts/gen_narration_gemini_sections.py` — --lang + fallback Edge-TTS.
- `scripts/build_composition.py` — --lang (título da capa no idioma).
- `scripts/description_template.py` — corrigido bug letra-por-coluna.
- `scripts/publish_multilang.py` — get_storyline retorna lista.

## Varredura do histórico (E:\videomaker\projects) — 53 projetos

### COMPLETOS (46) — pt + en + es com MP4
Os 40 originais + 6 novos publicados:
- golden-retriever-por-que-ele-e-o-melhor (en+es OK)
- saga-do-osso-de-ouro-34-o-guardiao-do-te (en+es OK)
- teste-10s-dentes-cachorro (en+es OK)
- teste-gemini-1min (en+es OK)
- um-dia-na-vida-de-um-cachorro-do-ponto-d (en+es OK)
- video-educativo-sobre-banho-em-cachorro (en+es OK)
- video-engracado-sobre-buldogue-ingles-00 (en+es OK)
- video-engracado-sobre-buldogue-ingles-divertido (en+es OK)

### FALHAM (2) — não foi possível completar
- vira-lata-caramelo-o-heroi-do-brasil: falha no timeline EN (ffmpeg concat de áudio). Es já completo.
- dachshund-marrom-luna-tenta-pegar-o-bisc: falta trilha sonora (bgm) para mix.

### SEM SCRIPT (3) — não podem ser traduzidos, pulados
- por-que-o-cachorro-gira-antes-de-deitar
- video-engracado-sobre-dachshund-SALSICHA
- v�deo-engra�ado-sobre-buldogue-ingles-01

## LISTA DE PUBLICACAO
Veja `LISTA_PUBLICACAO.md` (6 vídeos prontos para upload EN/ES).

## Execução em andamento
Nenhuma. Loop concluído para os 8 projetos processáveis.
