# -*- coding: utf-8 -*-
"""
Gera artifacts/script.json a partir de um prompt, usando o Gemini WEB
(chrome via CDP, scripts/gemini_fetch.py --kind text) — sem chamar API direta.

Fluxo:
  1. Monta um SYSTEM prompte pedindo ao Gemini um roteiro estruturado em JSON.
  2. Chama gemini_fetch.py --kind text --prompt "<SYSTEM>\n\nTEMA: ...".
  3. Le o .md gerado em artifacts/gemini/, extrai o JSON e grava artifacts/script.json.

Uso:
  python scripts/generate_script_from_prompt.py --prompt "Video engraçado sobre buldogue inglês"
  python scripts/generate_script_from_prompt.py --prompt "..." --out artifacts/script.json
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent

from narration_contract import apply_contract, validate_contract


SYSTEM = (
    "Voce e um escritor de historias infantis, em portugues do Brasil. "
    "Escreva uma HISTORIA ORIGINAL, divertida e carinhosa sobre o tema do usuario. "
    "Voce trabalha apenas com palavras: o texto da historia sera lido em voz alta "
    "por um narrador, por isso use frases curtas, pausas e exclamacoes.\n\n"
    "Responda SEMPRE com um JSON valido puro, sem markdown, sem texto antes ou depois, "
    "com exatamente esta estrutura:\n"
    '{"title": "Titulo curto e chamativo",\n'
    ' "sections": [\n'
    '  {"id": "s_intro", "label": "Introdução do Vídeo",\n'
    '   "text": "<gancho de entrada inteligente, criado com base no assunto. Deve despertar curiosidade nos primeiros segundos, fazer uma pergunta intrigante ou criar uma situacao inesperada relacionada ao tema. Exemplo: se o tema for escola de cachorros, algo como: E se um cachorro pudesse ir para a escola? Ja imaginou como sera?. Nao use sempre a mesma frase - crie algo unico para cada topico.>."',
    '   "delivery_cues": {"pace": "brisk", "energy": "curioso e empolgado",\n'
    '                     "emphasis_words": [], "pause_after_seconds": 0.8}},\n'
    '  {"id": "s0", "label": "Apresentação do Canal",\n'
    '   "text": "<saudacao de boas-vindas VARIAVEL e divertida para criancas, NAO robótica. Exemplo: \"Oiê, pessoal! Que bom que voces estao aqui com a gente! Hoje vamos falar de <assunto>.\" ou \"E ai, galera! Sejam bem-vindos ao canal da Frida e da Luna! Hoje temos uma historia imperdível sobre <assunto>.\". Variar a frase a cada video.>."',
    '   "delivery_cues": {"pace": "conversational", "energy": "alegre e acolhedor",\n'
    '                     "emphasis_words": [], "pause_after_seconds": 0.6}},\n'
    '  {"id": "s1", "label": "Gancho da Historia", "text": "...",\n'
    '   "delivery_cues": {"pace": "brisk", "energy": "alegre",\n'
    '                     "emphasis_words": ["..."], "pause_after_seconds": 0.6}},\n'
    '  {"id": "s_final", "label": "O vídeo acabou",\n'
    '   "text": "<aviso de que a historia terminou, falando que esse eh o final da nossa historia. Exemplo: \"E assim termina nossa aventura de hoje! Esse eh o final da nossa historia!\".>."',
    '   "delivery_cues": {"pace": "measured", "energy": "carinhoso",\n'
    '                     "emphasis_words": [], "pause_after_seconds": 0.6}},\n'
    '  {"id": "s_outro", "label": "Agradecimento",\n'
    '   "text": "<agradecimento e chamado a acao VARIAVEL: deixe seu like, se inscreva no canal e indique para seus amiguinhos. Variar a frase a cada video.>."',
    '   "delivery_cues": {"pace": "measured", "energy": "carinhoso",\n'
    '                     "emphasis_words": ["obrigado", "coracao", "Deus", "aventura"],\n'
    '                     "pause_after_seconds": 0.8}}\n'
    ' ]}\n\n'
    "Regras obrigatorias de abertura e encerramento (contrato do canal):\n"
    "- A PRIMEIRA secao e SEMPRE a s_intro, label 'Introdução do Vídeo'. Crie um gancho inteligente e unico baseado no assunto do video, despertando curiosidade nos primeiros segundos. Nao use sempre a mesma frase.\n"
    "- A SEGUNDA secao e SEMPRE a s0, label 'Apresentação do Canal'. e uma SAUDACAO DE BOAS-VINDAS VARIAVEL e divertida para criancas (ex: \"Oiê, pessoal!\", \"E ai, galera!\", \"Ola, lindos e lindas!\"). NAO use sempre a mesma frase; evite soar robotica. Nao comeca com cumprimentos genericos proibidos.\n"
    "- ANTES do agradecimento final, inclua a secao s_final, label 'O vídeo acabou', com um aviso de que a historia terminou (ex: \"E assim termina nossa aventura de hoje! Esse eh o final da nossa historia!\").\n"
    "- A ULTIMA secao e SEMPRE a s_outro, label 'Agradecimento'. e um agradecimento + chamado a acao VARIAVEL: deixe seu like, se inscreva no canal, indique para seus amiguinhos. NAO use sempre a mesma frase.\n"
    "- Nao escreva risadas (Hahaha!) na s_intro, s0, s_final nem na s_outro.\n\n"
    "Regras gerais:\n"
    "- **SIGA EXATAMENTE a premissa do TEMA DO USUARIO.** O elemento central pedido\n"
    "  (personagem, animal, objeto ou lugar) DEVE conduzir a historia do inicio ao fim.\n"
    "  E PROIBIDO substituir o tema por outro: se o tema pede 'cachorro astronauta verde',\n"
    "  a historia tem que ser sobre esse cachorro; nao invente osso magico, tesouro,\n"
    "  queijo especial ou outro objeto como foco.\n"
    "- **Cenario consistente:** todo o video acontece no mesmo cenario/ambiente definido pelo tema.\n"
    "  Se o tema for 'zoologico', todas as cenas acontecem no zoologico. Se for 'Marte',\n"
    "  todas as cenas acontecem em Marte (ou na nave que vai pra Marte e de volta a Terra).\n"
    "  Nao mude de cenario aleatoriamente: nao ponha grama se o tema e Marte, nem casa\n"
    "  se o tema e o zoologico. O pano de fundo e o mesmo do começo ao fim.\n"
    "- **Licao educativa:** toda historia infantil deve ensinar algo para as criancas.\n"
    "  No final da historia (antes da s_final), inclua uma secao extra com a licao/moral\n"
    "  da historia (ex: 'O que aprendemos hoje? Ser gentil com os outros e importante.').\n"
    "  Essa licao deve ficar clara no texto da ultima secao de historia ou na s_final.\n"
    "- Gere de 8 a 14 secoes de HISTORIA (s1, s2, ...), MAIS a s_final (aviso de fim) e a s_outro (agradecimento) no fim.\n"
    "- **Cada secao de historia deve ter de 55 a 80 palavras** (a s0, de 25 a 45).\n"
    "- ids: s_intro (gancho), s0 (saudacao), s1, s2, ... para a historia, s_final (aviso de fim) e a ultima secao SEMPRE tem id s_outro.\n"
    "- Texto: frases curtas, com pausas (...) e exclamacoes para dar energia.\n"
    "- O text de cada secao e APENAS o que o narrador fala em voz alta. PROIBIDO\n"
    "  incluir ficha de personagens ou descricao fisica no text.\n"
    "- delivery_cues.pace: uma de slow, measured, conversational, brisk, fast.\n"
    "- delivery_cues.emphasis_words: palavras que o narrador deve destacar.\n"
    "- delivery_cues.pause_after_seconds: apos a secao (0.4 a 1.2).\n"
    "- Tom: alegre, envolvente, como um documentario que vira piada.\n"
    "- Inclua risadas: ao menos uma Hahaha! em cada secao de historia, logo apos\n"
    "  uma frase engraçada ou surpreendente. A risada deve ser lida em voz alta\n"
    "  pelo narrador (nunca na s0 nem na s_outro).\n"
    "- Use exclamacoes (!) para dar energia.\n"
    "- PROIBIDO citar Pixar, Disney, Ghibli, DreamWorks, Illumination ou qualquer "
    "estudio/marca.\n"
    "- Se o tema for sobre Frida e Luna: Frida é buldogue inglês (cachorra) e "
    "Luna é salsicha/dachshund (cachorra). NUNCA as chame de gata, gatinha ou felina. "
    "Sem humanos na historia (nada de vovó, tutor, dono).\n"
    "- Apelidos carinhosos do canal: Frida é a Fridóca e Luna é a Luninha. Use os "
    "apelidos com carinho na narração, sem trocar os nomes oficiais.\n"
)


DEFAULT_STYLE_NOTES = "ilustracao colorida, luz suave, clima alegre e acolhedor"


FICHA_RE = re.compile(
    r"^(?:\s*Luna[,:]\s*.{0,400}?Frida[,:]\s*.{0,400}?Visual\s*:.*?exagerad\w*\.?\s*)",
    re.I | re.S,
)


def strip_character_sheet_prefix(text):
    """Remove prefixo de ficha de personagens que o modelo pode colar no text
    de cada secao (ex.: 'Luna: cadela dachshund..., Frida: ..., Visual: ...').
    So age quando a secao comeca com o padrao; texto de historia intacto nao
    e alterado."""
    t = (text or "").strip()
    for _ in range(2):
        m = FICHA_RE.match(t)
        if not m:
            break
        t = t[m.end():].strip()
    return t if len(t) >= 20 else (text or "")


def extract_json(text):
    """Extrai o melhor objeto JSON valido com 'sections' de um texto.

    Tolera markdown fences, prosa e respostas concatenadas (uma versao truncada
    seguida de uma versao completa). Usa raw_decode a partir de cada ocorrencia
    de '{"title"' e fica com o objeto de mais secoes.
    """
    dec = json.JSONDecoder()
    melhor = None
    for m in re.finditer(r'\{\s*"title"', text):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("sections"):
            if melhor is None or len(obj["sections"]) >= len(melhor["sections"]):
                melhor = obj
    if melhor is not None:
        return melhor

    # Tenta achar fences de codigo
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        blob = m.group(1)
    else:
        # fallback: primeiro '{' ate o ultimo '}'
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("nenhum objeto JSON encontrado na resposta")
        blob = text[start:end + 1]
    return json.loads(blob)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", default=str(PROJECT / "artifacts" / "script.json"))
    ap.add_argument("--name", default="script_text")
    ap.add_argument("--wait", type=int, default=120)
    args = ap.parse_args()

    fetch = HERE / "gemini_fetch.py"
    out_dir = Path(args.out).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    full_prompt = "".join(SYSTEM) + "\n\nTEMA DO USUARIO: " + args.prompt

    cmd = [
        sys.executable, str(fetch),
        "--kind", "text",
        "--prompt", full_prompt,
        "--name", args.name,
        "--out-dir", str(out_dir),
        "--wait", str(args.wait),
    ]
    print("== Chamando gemini_fetch.py --kind text ...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FALHOU: gemini_fetch.py")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        return 1
    print(r.stdout[-1500:])

    # Encontra o arquivo .md gerado (o mais recente com o name informado).
    # gemini_fetch salva em <out-dir>/<name>.md (ou <out-dir>/gemini/<name>.md se out-dir for o padrão).
    candidates = []
    for d in (out_dir, out_dir / "gemini"):
        if d.exists():
            candidates += sorted(d.glob(args.name + ".*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("ERRO: nao achei arquivo gerado em", out_dir, "ou", out_dir / "gemini")
        return 1
    md = candidates[0]
    print("== Lendo resposta em:", md)
    text = md.read_text(encoding="utf-8", errors="ignore")

    script = extract_json(text)
    script.setdefault("style_notes", DEFAULT_STYLE_NOTES)
    for s in script.get("sections", []):
        limpo = strip_character_sheet_prefix(s.get("text", ""))
        if limpo != s.get("text", ""):
            print("SANITIZADO: secao %s tinha prefixo de ficha de personagens (removido)" % s.get("id", "?"))
            s["text"] = limpo

    # Contrato de abertura/encerramento: garante o texto humanizado mesmo que
    # o modelo ignore as instrucoes (fonte unica: narration_contract.py).
    script, mudancas = apply_contract(script, theme=script.get("title") or args.prompt)
    for c in mudancas:
        print("CONTRATO:", c)
    problemas = validate_contract(script)
    if problemas:
        print("ERRO: contrato de narracao invalido:", "; ".join(problemas))
        return 1

    out = Path(args.out)
    out.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    print("roteiro gravado:", out, "| secoes:", len(script.get("sections", [])))
    for s in script.get("sections", []):
        print("  %-4s %-22s %4d palavras" % (s.get("id", ""), s.get("label", ""), len(s.get("text", "").split())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
