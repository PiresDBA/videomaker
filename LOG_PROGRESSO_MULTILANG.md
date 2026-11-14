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

## 2026-11-13 - Travas contra imagem repetida, imagem por idioma e MP4 velho

Fecha o ciclo do bug da figura repetida (Chihuahua ~1:22, Restaurante do inicio
ao fim). Alem da correcao de prompt/download, o erro agora e bloqueado antes de
acontecer:

- check_prompt_repeticao.py: frase proibida em prompt (copiar a referencia),
  --strict exige CENA prioridade + REGRA ANTI-REPETICAO + scene_mode=two, e
  testa build_prompt com cena longa (o corte de MAX_PROMPT_CHARS estava comendo
  a regra nas variantes _b).
- check_imagens_repetidas.py: duas imagens de cena iguais = falha.
- check_imagens_compartilhadas.py: manifesto sha1; PT/EN/ES tem que usar as
  MESMAS imagens; confere antes de cada render.
- gerar_capitulo_trilinguo.py: trava() antes das imagens e antes de cada
  render; MP4 so e reaproveitado se for mais novo que imagens/roteiro/overlays/
  narracao (antes reaproveitou video velho depois de regerar as imagens).
- .githooks/pre-commit e pre-push + scripts/install_hooks.py.
- Docs: CONTRATO 4.7-4.11, 5.8, 5.9, 5.10; MANUAL 58.2.1, 58.6.1, 58.6.2;
  AGENTS com bloco de parada obrigatoria.

Estado das imagens (mesma pasta para os 3 idiomas):
- Chihuahua: 27 imagens novas conferidas (Frida buldogue, Luna salsicha,
  chihuahua de pelo curto), 3 renders em andamento.
- Restaurante: 9/27 imagens novas; retomar da 10a e renderizar.
- Videos errados ainda no ar: Chihuahua PT/EN e Restaurante PT/EN - apagar com
  o token do canal dono assim que os renders novos existirem.

## 2026-11-13 - Publicacao Chihuahua (apos remocao dos videos errados)

Videos errados apagados (antes de republicar):
- Chihuahua PT: Rpu0kECUvtA
- Chihuahua EN: sO6oQ3CvhRU
- Restaurante PT: kdopBwWCVT0
- Restaurante EN: kpqb0dDd-y4

Chihuahua republicado (figuras corretas, 3 idiomas, imagens compartilhadas PT/EN/ES):
- PT: https://youtu.be/jvi-hxayVVI
- EN: https://youtu.be/0GlS-s0r2D8
- ES: https://youtu.be/yp1z5Qi5mL0

Restaurante (bulldogue-ingles-frida-e-dachshund-marro):
- Ainda gerando em background (retomando da 10a imagem; 9/27 ja feitas).
- Nao tem versao EN nem ES ainda - so sao renderizadas apos concluir as 27 imagens.
- Publicar PT/EN/ES assim que o render terminar; ES depende da cota diaria do canal.


## 2026-11-14 - o-co-de-frias: imagens e PT prontos; EN/ES em geracao

O aviso anterior de "travado na fase images" estava desatualizado: as imagens
terminaram as 23:14 de 13/11 e o pipeline seguiu sozinho.

Estado real:
- Imagens: 28/28 geradas pelo Google Flow, travas de prompt/imagem OK
  (nenhuma figura repetida; manifesto PT/EN/ES gravado).
- PT: narracao + legendas 08:51, timeline 08:52, mix/compose/preprocess
  08:52, render 08:59 (`output/o-co-de-frias_pt.mp4`, 178,7 s, 176 MB).
- Quadros conferidos em 0:12, 1:20 e 2:40: cenas diferentes, Frida (buldogue)
  e Luna (salsicha) com o design correto.
- EN/ES: gerando com as MESMAS 28 imagens (nada de imagem nova por idioma).
- Fila de temas: `scripts/topics.txt` documentada em CONTRATO 5.11,
  MANUAL 58.7 e AGENTS; o tema "O cao de ferias" foi registrado em USADOS.
- Restaurante republicado com as imagens novas: PT https://youtu.be/LlxLDkWWViU,
  ES ja estava no ar: aS0hSOX4U1Y.
- Restaurante EN: o primeiro envio (Xy1Ha07ot-Y) narrava uma RECUSA do Gemini
  ("Nao posso te ajudar... sou apenas um modelo de linguagem") nos blocos s6 e
  s_final. O video foi apagado do canal e republicado depois do re-render com o
  script_en corrigido: https://youtu.be/kh00OU09Tks (14/11, 3m59).
  Causa tratada em `translate_script.py` (recusa descartada) e no check novo
  `check_texto_idioma.py`.
- Chihuahua PT: a duplicata antiga GCg3M6z3CC0 (render velho, 10:43) foi
  apagada; o PT correto e jvi-hxayVVI.
- o-co-de-frias PT: xCucNQcKFCc (09:39:50) — publicado.
- o-co-de-frias EN: chuPVCBuK3Q (10:02:11) — publicado.
- o-co-de-frias ES: render em andamento (56% concluída), publicar após finalização.
- Restaurante ES: aS0hSOX4U1Y (19:48:26) — publicado com PT badge "Frida e Luna"
  (PT) no overlay; re-render e re-publicar planejado para limpar PT/ES.


