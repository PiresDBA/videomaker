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

## 2026-11-12 — Correção do idioma dos metadados + 3 canais

### Bug corrigido
Título e gancho da descrição usavam tradução "na hora" via `gemini_fetch.py`.
Quando o Gemini falhava, caía no título em PT e subia para o canal EN/ES.
Agora título/enredo vêm SEMPRE de `artifacts/script_<lang>.json`; se faltar,
o upload aborta. Os 6 vídeos errados dos canais EN/ES foram apagados e
reenviados com metadados corretos.

### Canais
- PT = canal principal (token histórico `youtube_token.json`, fallback)
- EN = `youtube_token_en.json` (autorizado, YouTube Data API v3 ativa)
- ES = `youtube_token_es.json` (autorizado)

### Estado (2026-11-12)
- EN: 5 publicados de 49 prontos
- ES: 5 publicados de 49 prontos
- PT: 33 de 46 prontos casados com o canal principal

### Limite real
Cota da API: ~6 uploads/canal/dia (`videos.insert` = 1600 de 10.000).
Rodar `python scripts/loop_upload_idiomas.py` 1x por dia até zerar os pendentes.

### Pendências
- 59 vídeos EN/ES antigos ainda estão no canal principal (PT); decidir se
  apaga depois de subir a cópia no canal certo.
- Capa/overframe dos MP4s antigos continua em PT (re-render futuro, §56.6 do manual).
- dachshund-marrom-luna-tenta-pegar-o-bisc sem trilha (bgm).
- 3 projetos sem `script.json` (não traduzíveis ainda).

## 2026-11-13 - Novo capitulo trilingue: "O Parque dos Pets"

Primeiro capitulo gerado pelo novo fluxo (gerar_capitulo_trilinguo.py, sec. 58
do manual): imagens SO pelo Google Flow (referencia Frida + Luna + --ref-image
da ultima imagem gerada para continuidade de cenario), roteiro/cenas/imagens/
musica gerados uma vez e reaproveitados pelos 3 idiomas.

### Videos
- PT: luna-e-frida-conhecem-um-parque-de-diver_pt.mp4 (3m16s) -> publicado
  https://youtu.be/1kxFAThSKas (legenda OK)
- EN: ..._en.mp4 (3m28s) -> publicado https://youtu.be/1wuBS1M7mCk (legenda OK)
- ES: ..._es.mp4 (3m35s) -> PENDENTE: YouTube recusou com uploadLimitExceeded
  (limite diario de uploads do CANAL, nao da API). Reenviar quando resetar (~24h):

  python scripts/upload_por_idioma.py es --projects-dir C:\videomaker\projects --slug luna-e-frida-conhecem-um-parque-de-diver

### Pendencias (continuam)
- ES deste capitulo (comando acima).
- PT: limpar duplicados <50 views por idioma de legenda
  (pt_menos_50_views_en_es.py --apagar, 40 pendentes da cota de ontem).
- EN/ES antigos: continuar upload_por_idioma.py en|es --all (ou
  loop_upload_idiomas.py) ate zerar.

## 2026-11-13 - BUG: imagem repetida em Chihuahua e Restaurante (RESOLVIDO)

Sintoma: Chihuahua repetia a mesma foto a partir de ~1:22; Restaurante repetia
a mesma figura do inicio ao fim.

Causa (2 camadas):
1. Os prompts mandavam copiar a referencia: "siga a imagem de referencia
   anexada para TUDO", "mantenha exatamente a mesma aparencia ... em todas as
   imagens" e "mantenha este mesmo ambiente em todas as imagens".
2. O flow_fetch salvava a miniatura da propria imagem de referencia (primeira
   resposta de imagem da pagina) em vez da imagem gerada - comprovado: arquivo
   salvo era pixel a pixel igual a referencia.

Correcao (manual §58.6):
- Referencia = design das personagens/estilo; a CENA manda em tudo.
- Bloco "REGRA ANTI-REPETICAO" em todo prompt; cenario = mesmo tipo de lugar
  com enquadramento/angulo/fundo diferentes.
- Bloco anti-texto movido para logo apos a CENA (nao e mais cortado por
  MAX_PROMPT_CHARS).
- flow_fetch: ignora respostas identicas a referencia e URLs ja presentes na
  tela; _imagem_repetida descarta e reenvia imagem igual a referencia ou a
  qualquer imagem existente na pasta.

Acao: 27 imagens regeradas por capitulo e 3 renders por capitulo. Videos
antigos (Chihuahua PT/EN, Restaurante PT/EN) devem ser apagados e reenviados.
