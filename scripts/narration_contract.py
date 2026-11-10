# -*- coding: utf-8 -*-
"""
Contrato de abertura e encerramento do canal "Frida e Luna".

Fonte unica da verdade para o texto humanizado de abertura e agradecimento.
Aplicado em:
  - generate_script_from_prompt.py (fase script)
  - gen_narration_edge.py (fase narration; repara roteiros antigos)
  - pipeline.py (validacao do checkpoint script)

Regra:
  - A primeira secao (id "s_intro") e o gancho/hook principal do video.
  - A segunda secao (id "s0") e a saudacao/boas-vindas, que DEVE variar de
    video para video (nunca ficar robótica/repetitiva).
  - Uma secao extra (id "s_final") avisa que a historia acabou, logo ANTES do
    agradecimento final.
  - A ultima secao (id "s_outro") e o agradecimento/CTA, que tambem deve variar
    (like, se inscrever, indicar para os amiguinhos).
  - Todas fazem parte do roteiro (cenas, narracao, timeline e grafo).
"""
import re
import unicodedata

# Nova secao de introducao (hook) que vem ANTES da saudacao
HOOK_PREFIX = (
    "E se "
)
HOOK_LABEL = "Introdução do Vídeo"
HOOK_ID = "s_intro"

# Labels fixos (estrutura). O texto vem do Gemini; esses so sao usados como
# fallback quando o texto esta vazio.
INTRO_LABEL = "Apresentação do Canal"
OUTRO_LABEL = "Agradecimento"
FINAL_LABEL = "O vídeo acabou"
FINAL_ID = "s_final"
OUTRO_ID = "s_outro"

# Fallbacks de saudacao variada (usados so se o Gemini nao gerar texto em s0).
INTRO_FALLBACKS = (
    "Olá amiguinhos e amiguinhas! Sejam bem-vindos ao nosso canal! Que legal que vocês vieram! Hoje a gente vai falar de {assunto}.",
    "Oiê, pessoal! Que bom que vocês estão aqui com a gente! Se preparem porque hoje temos uma história bem divertida sobre {assunto}.",
    "E ai, galera! Sejam bem-vindos ao canal da Frida e da Luna! Hoje vamos contar uma história imperdível sobre {assunto}.",
    "Olá, lindos e lindas! Que alegria ter vocês aqui! Vem com a gente que hoje a aventura é sobre {assunto}.",
)

# Fallbacks de aviso de fim (usados so se o Gemini nao gerar s_final).
FINAL_FALLBACKS = (
    "É, essa é o fim da nossa história por hoje! Esse foi o final, amiguinhos!",
    "Chegamos ao final! Essa é a última parte da nossa história, tchau por enquanto!",
    "E assim termina nossa aventura de hoje! Esse é o final da nossa história!",
    "Acabou! Essa é a última cena da nossa história, obrigado por assistir até aqui!",
)

# Bloco canonico de encerramento. "No nosso coracao" (ex: "acompanhar essa
# aventura no nosso coracao") nao e uma frase humana; o unico uso aceito de
# coracao no encerramento e "um grande beijo no seu coracao".
HEART_BLOCK = (
    "Um grande beijo no seu coração e fique com a gente! "
    "Acompanhe nossos próximos vídeos!"
)

# Fallbacks de agradecimento/CTA variado (usados so se o Gemini nao gerar texto em s_outro).
OUTRO_FALLBACKS = (
    "Muito obrigado por acompanhar essa linda aventura! Um grande beijo no seu coração e fique com a gente! Acompanhe nossos próximos vídeos! Deixe seu like, se inscreva no canal e indique para seus amiguinhos!",
    "Obrigado por assistir! Um grande beijo no seu coração e fique com a gente! Acompanhe nossos próximos vídeos! Deixe seu like e se inscreva no canal para não perder nenhuma aventura da Luninha e da Fridóca!",
    "Muito obrigado por ficar até o final! Um grande beijo no seu coração e fique com a gente! Acompanhe nossos próximos vídeos! Curta o vídeo, se inscreva no canal e mande para seus amiguinhos!",
    "Obrigado por acompanhar a gente! Um grande beijo no seu coração e fique com a gente! Acompanhe nossos próximos vídeos! Deixe o like, se inscreva no canal e compartilhe com seus amiguinhos!",
)

_INTRO_RE = re.compile(r"^\s*ol[áa]\s*amiguinhos\s*e\s*amiguinhas!", re.I)
_BAD_OPEN_RE = re.compile(
    r"^\s*(?:ol[áa],?\s*(?:fam[íi]lia|pessoal|gente|galera)"
    r"|ol[áa],?\s*amiguinhos\s*(?:!|,|\s*$)"
    r"|oi,?\s*(?:fam[íi]lia|pessoal|galera))",
    re.I,
)
_HOOK_RE = re.compile(r"^\s*e\s*se\s+[^\?]+\?", re.I)
_LAUGH_RE = re.compile(r"(?i)\b(?:ha[\s\-!]*){2,}[!\.,]?")
_OUTRO_HINTS = (
    "obrigad",
    "tchau",
    "ate a proxima",
    "se inscrev",
    "deixe o like",
    "deixa o like",
    "joinha",
    "curta o video",
)


def _fold(text):
    """Minusculas sem acentos (para comparacoes tolerantes)."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def _norm(text):
    return " ".join((text or "").split())


def _strip_laugh(text):
    return _norm(_LAUGH_RE.sub(" ", text or ""))


def clean_theme(theme):
    """Normaliza o assunto usado na frase de abertura."""
    original = _norm(theme)
    t = re.sub(r"^(?:t[íi]tulo|tema|assunto)\s*:\s*", "", original, flags=re.I)
    t = t.strip(" .!?:;-")
    if original.rstrip().endswith("?"):
        t += "?"
    return t


def _pick_fallback(options, key):
    """Escolhe um fallback de forma determinística a partir da chave (assunto)."""
    if not options:
        return ""
    import hashlib
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


def build_intro(theme):
    """Saudacao de boas-vindas (s0). Variavel: escolhe um dos fallbacks com
    base no assunto, mas o ideal e que o Gemini gere um texto unico."""
    t = clean_theme(theme)
    if not t:
        t = "uma aventura nova com a Frida e a Luna"
    fallback = _pick_fallback(INTRO_FALLBACKS, t).format(assunto=t)
    return _strip_laugh(fallback)


def build_hook(theme):
    """Frase de introducao (hook) que vem ANTES da saudacao.

    Usada como fallback se o Gemini nao gerar a secao s_intro.
    O ideal eh que o Gemini crie um gancho unico baseado no assunto.
    """
    t = clean_theme(theme)
    if not t:
        t = "uma aventura nova com a Frida e a Luna"
    t = t.rstrip(".!?")
    return "E se " + t + "? Já imaginou como será?"


def build_final(theme):
    """Aviso de fim de historia (s_final). Variavel: fallback baseado no assunto."""
    t = clean_theme(theme)
    if not t:
        t = "uma aventura nova com a Frida e a Luna"
    fallback = _pick_fallback(FINAL_FALLBACKS, t).format(assunto=t)
    return _strip_laugh(fallback)


def build_outro(theme):
    """Agradecimento/CTA final (s_outro). Variavel: fallback baseado no assunto."""
    t = clean_theme(theme)
    if not t:
        t = "uma aventura nova com a Frida e a Luna"
    fallback = _pick_fallback(OUTRO_FALLBACKS, t).format(assunto=t)
    return _strip_laugh(fallback)


_BAD_HEART_RE = (
    re.compile(r"(?i)\bfique\s+com\s+o\s+nosso\s+cora[çc][ãa]o\b"),
    re.compile(r"(?i)\b(?:acompanh\w*)\s+(?:o\s+|esse\s+|este\s+)?nosso\s+cora[çc][ãa]o\b"),
    re.compile(r"(?i)\b(?:no|com\s+o)\s+nosso\s+cora[çc][ãa]o\b"),
)
_HEART_ORDER_RE = re.compile(
    r"(?i)um\s+beijo\s+grande\s+no\s+seu\s+cora[çc][ãa]o"
)


def _heart_order(match):
    rep = "um grande beijo no seu coração"
    return rep[:1].upper() + rep[1:] if match.group(0)[:1].isupper() else rep


def sanitize_heart_phrase(text):
    """Corrige o encerramento para soar humano.

    - Remove "no nosso coração" / "fique com o nosso coração" / "acompanhe
      nosso coração" (frases que ninguém fala).
    - Normaliza "um beijo grande no seu coração" -> "um grande beijo no seu
      coração".
    - Garante o bloco canonico "Um grande beijo no seu coração e fique com a
      gente! Acompanhe nossos próximos vídeos!".
    """
    t = _norm(text)
    if not t:
        return t
    for rx in _BAD_HEART_RE:
        t = rx.sub(" ", t)
    t = re.sub(r"(?i)\s+e\s*([.!?,])", r"\1", t)
    t = re.sub(r"(?i)^\s*e\b\s*", "", t)
    t = re.sub(r"(?i)\s+([,\.!?;:])", r"\1", t)
    t = re.sub(r"^[\s,;.!?]+", "", t)
    t = _norm(t)
    t = _HEART_ORDER_RE.sub(_heart_order, t)

    chaves = (
        "um grande beijo no seu coracao",
        "fique com a gente",
        "acompanhe nossos proximos videos",
    )
    low = _fold(t)
    if all(k in low for k in chaves):
        return _norm(t)

    # Remove qualquer frase parcial de coracao para nao duplicar o bloco.
    frases = re.split(r"(?<=[.!?])\s+", t)
    frases = [f for f in frases
              if not ("beijo" in _fold(f) and "coracao" in _fold(f))]
    t = _norm(" ".join(frases))
    m = re.match(r"^(.*?[.!?])\s+(.*)$", t, re.S)
    if m:
        t = _norm(m.group(1)) + " " + HEART_BLOCK + " " + _norm(m.group(2))
    elif t:
        t = _norm(t) + " " + HEART_BLOCK
    else:
        t = HEART_BLOCK
    return _norm(t)


def _looks_like_outro(text, label):
    low = _fold((label or "") + " " + (text or ""))
    return any(h in low for h in _OUTRO_HINTS)


def _unique_id(base, used):
    if base not in used:
        return base
    n = 2
    while "%s_%d" % (base, n) in used:
        n += 1
    return "%s_%d" % (base, n)


def _set(section, key, value, changes, sid):
    if section.get(key) != value:
        section[key] = value
        changes.append("%s.%s" % (sid, key))


def apply_contract(script, theme=None):
    """Aplica o contrato no dicionario do roteiro (in-place).

    Garante a ESTRUTURA (ids, labels e ordem: s_intro -> s0 -> conteudo ->
    s_final -> s_outro) mas NAO sobescreve textos que o Gemini ja gerou, para
    que saudacao, aviso de fim e CTA possam variar de video para video.
    Fallbacks sao usados apenas quando uma secao esta vazia.

    Retorna (script, changes). E idempotente.
    """
    changes = []
    sections = script.get("sections") or []
    if not sections:
        return script, ["script sem secoes"]

    assunto = theme or script.get("title") or script.get("theme") or ""
    hook = build_hook(assunto)
    intro = build_intro(assunto)
    final_txt = build_final(assunto)
    outro_txt = build_outro(assunto)

    if len(sections) < 2:
        script["sections"] = sections
        return script, ["script com menos de 2 secoes; contrato nao aplicado"]

    # ---------- secao de introducao (s_intro) ----------
    hook_idx = next((i for i, s in enumerate(sections) if s.get("id") == HOOK_ID), None)
    if hook_idx is None:
        hook_section = {
            "id": HOOK_ID,
            "label": HOOK_LABEL,
            "text": hook,
            "delivery_cues": {
                "pace": "brisk",
                "energy": "curioso e empolgado",
                "emphasis_words": [],
                "pause_after_seconds": 0.8,
            },
        }
        sections.insert(0, hook_section)
        changes.append("secao de introducao adicionada (s_intro)")
    else:
        if hook_idx != 0:
            sections.insert(0, sections.pop(hook_idx))
            changes.append("secao de introducao movida para o inicio")
        atual = sections[0]
        if not (atual.get("text") or "").strip():
            _set(atual, "text", hook, changes, HOOK_ID)
        _set(atual, "label", HOOK_LABEL, changes, HOOK_ID)

    # ---------- abertura (s0) ----------
    # s0 deve ficar imediatamente depois de s_intro.
    used = {s.get("id") for s in sections if s.get("id") != "s0"}
    first = sections[1] if len(sections) > 1 else None
    if first is None or first.get("id") != "s0":
        # procura uma secao s0 em qualquer lugar e promove
        s0_idx = next((i for i, s in enumerate(sections) if s.get("id") == "s0"), None)
        if s0_idx is not None and s0_idx != 1:
            sections.insert(1, sections.pop(s0_idx))
            changes.append("abertura promovida para posicao apos o gancho")
        elif s0_idx is None:
            nova = {
                "id": "s0",
                "label": INTRO_LABEL,
                "text": intro,
                "delivery_cues": {
                    "pace": "conversational",
                    "energy": "alegre e acolhedor",
                    "emphasis_words": [],
                    "pause_after_seconds": 0.6,
                },
            }
            sections.insert(1, nova)
            changes.append("secao de abertura criada (s0)")
    first = sections[1]
    _set(first, "id", "s0", changes, "s0")
    _set(first, "label", INTRO_LABEL, changes, "s0")
    if not (first.get("text") or "").strip():
        _set(first, "text", intro, changes, "s0")

    # ---------- aviso de fim (s_final) ----------
    # Deve ficar entre o ultimo conteudo e o agradecimento.
    final_idx = next((i for i, s in enumerate(sections) if s.get("id") == FINAL_ID), None)
    if final_idx is None:
        # insere antes do s_outro (que esta no final ou sera movido para lá)
        outro_idx = next((i for i, s in enumerate(sections)
                          if s.get("id") == OUTRO_ID), len(sections))
        nova_final = {
            "id": FINAL_ID,
            "label": FINAL_LABEL,
            "text": final_txt,
            "delivery_cues": {
                "pace": "measured",
                "energy": "carinhoso",
                "emphasis_words": [],
                "pause_after_seconds": 0.6,
            },
        }
        sections.insert(outro_idx, nova_final)
        changes.append("secao de aviso de fim criada (s_final)")
    else:
        atual = sections[final_idx]
        _set(atual, "id", FINAL_ID, changes, FINAL_ID)
        _set(atual, "label", FINAL_LABEL, changes, FINAL_ID)
        if not (atual.get("text") or "").strip():
            _set(atual, "text", final_txt, changes, FINAL_ID)

    # ---------- encerramento (s_outro) ----------
    used_ids = {s.get("id") for s in sections}
    outro_idx = None
    for i, s in enumerate(sections):
        if s.get("id") == OUTRO_ID or _fold(s.get("label", "")).find("agradec") >= 0:
            outro_idx = i
            break
    if outro_idx is not None:
        outro = sections.pop(outro_idx)
        used_ids.discard(outro.get("id"))
        new_id = _unique_id(OUTRO_ID, used_ids)
        _set(outro, "id", new_id, changes, "outro")
        _set(outro, "label", OUTRO_LABEL, changes, new_id)
        atual_outro = outro.get("text") or ""
        _set(outro, "text", sanitize_heart_phrase(atual_outro or outro_txt),
             changes, new_id)
        sections.append(outro)
    else:
        new_id = _unique_id(OUTRO_ID, used_ids)
        outro = {
            "id": new_id,
            "label": OUTRO_LABEL,
            "text": sanitize_heart_phrase(outro_txt),
            "delivery_cues": {
                "pace": "measured",
                "energy": "carinhoso",
                "emphasis_words": ["obrigado", "coração", "Deus", "aventura"],
                "pause_after_seconds": 0.8,
            },
        }
        sections.append(outro)
        changes.append("secao de agradecimento criada (%s)" % new_id)

    script["sections"] = sections
    return script, changes


def validate_contract(script):
    """Lista de problemas do contrato (vazia = roteiro em conformidade)."""
    issues = []
    sections = script.get("sections") or []
    if not sections:
        return ["script sem secoes"]

    # ---------- validacao da secao de introducao (s_intro) ----------
    first = sections[0]
    if first.get("id") != HOOK_ID:
        issues.append("a primeira secao deve ter id '%s'" % HOOK_ID)
    hook_text = first.get("text", "").strip()
    if not hook_text:
        issues.append("s_intro nao pode ficar vazia")
    elif len(hook_text.split()) < 3:
        issues.append("s_intro precisa ter pelo menos 3 palavras (gancho muito curto)")

    # ---------- validacao da abertura (s0) ----------
    if len(sections) < 2:
        issues.append("script precisa ter pelo menos s_intro e s0")
    else:
        s0 = sections[1]
        if s0.get("id") != "s0":
            issues.append("a segunda secao deve ter id 's0'")
        intro_text = s0.get("text", "")
        if not intro_text.strip():
            issues.append("s0 nao pode ficar vazia (saudacao/boas-vindas)")
        if _BAD_OPEN_RE.match(intro_text):
            issues.append("s0 ainda comeca com cumprimento antigo ('Olá, família!')")
        if "hahaha" in _fold(intro_text):
            issues.append("s0 nao pode ter risada escrita")

    last = sections[-1]
    if last.get("id") != OUTRO_ID:
        issues.append("a ultima secao deve ter id '%s'" % OUTRO_ID)
    if _fold(last.get("label", "")) != _fold(OUTRO_LABEL):
        issues.append("a ultima secao deve ter label '%s'" % OUTRO_LABEL)
    if not last.get("text", "").strip():
        issues.append("s_outro nao pode ficar vazio (agradecimento/CTA)")
    outro_low = _fold(last.get("text", ""))
    if "nosso coracao" in outro_low:
        issues.append("s_outro usa 'no nosso coração' (frase nao humana); "
                      "use 'um grande beijo no seu coração e fique com a gente'")
    if "coracao" in outro_low and \
            "um grande beijo no seu coracao" not in outro_low:
        issues.append("s_outro deve usar 'um grande beijo no seu coração' "
                      "quando falar de coração")

    ids = [s.get("id") for s in sections]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        issues.append("ids duplicados: %s" % ", ".join(dups))
    return issues
