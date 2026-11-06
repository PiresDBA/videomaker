# -*- coding: utf-8 -*-
"""
Contrato de abertura e encerramento do canal "Frida e Luna".

Fonte unica da verdade para o texto humanizado de abertura e agradecimento.
Aplicado em:
  - generate_script_from_prompt.py (fase script)
  - gen_narration_edge.py (fase narration; repara roteiros antigos)
  - pipeline.py (validacao do checkpoint script)

Regra:
  - A primeira secao (id "s0") SEMPRE comeca com o cumprimento humanizado.
  - A ultima secao (id "s_outro") SEMPRE e o agradecimento humanizado.
  - As duas secoes fazem parte do roteiro (e, portanto, das cenas, da
    narracao, da timeline e do grafo).
"""
import re
import unicodedata

INTRO_PREFIX = (
    "Olá amiguinhos e amiguinhas! Tudo bem com vocês? Que legal ter vocês aqui com a gente! "
    "Hoje a gente vai falar de "
)
INTRO_LABEL = "Apresentação do Canal"

OUTRO_TEXT = (
    "Muito obrigado por assistir nossos vídeos, um beijo grande no seu coração, "
    "fique com Deus e até a nossa próxima aventura, tchau tchau!!"
)
OUTRO_LABEL = "Agradecimento"
OUTRO_ID = "s_outro"

_INTRO_RE = re.compile(r"^\s*ol[áa]\s*amiguinhos\s*e\s*amiguinhas!", re.I)
_BAD_OPEN_RE = re.compile(
    r"^\s*(?:ol[áa],?\s*(?:fam[íi]lia|pessoal|gente|galera)"
    r"|ol[áa],?\s*amiguinhos\s*(?:!|,|\s*$)"
    r"|oi,?\s*(?:fam[íi]lia|pessoal|galera))",
    re.I,
)
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


def build_intro(theme):
    """Frase de abertura humanizada, preenchida com o assunto do video."""
    t = clean_theme(theme)
    if not t:
        t = "uma aventura nova com a Frida e a Luna"
    suffix = "" if t.endswith(("?", "!", ".")) else "."
    return _strip_laugh(INTRO_PREFIX + t + suffix)


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

    Retorna (script, changes). E idempotente: rodar duas vezes nao duplica
    secoes nem altera o texto final.
    """
    changes = []
    sections = script.get("sections") or []
    if not sections:
        return script, ["script sem secoes"]

    assunto = theme or script.get("title") or script.get("theme") or ""
    intro = build_intro(assunto)

    if len(sections) < 2:
        script["sections"] = sections
        return script, ["script com menos de 2 secoes; contrato nao aplicado"]

    # ---------- abertura (s0) ----------
    first = sections[0]
    used = {s.get("id") for s in sections if s is not first}
    if first.get("id") != "s0":
        first["id"] = "s0"
        changes.append("abertura promovida para s0")
    used.add("s0")
    _set(first, "id", "s0", changes, "s0")
    _set(first, "label", INTRO_LABEL, changes, "s0")
    _set(first, "text", intro, changes, "s0")

    # ---------- encerramento (s_outro) ----------
    last_idx = len(sections) - 1
    outro_idx = None
    for i, s in enumerate(sections):
        if i == 0:
            continue
        if s.get("id") == OUTRO_ID or _fold(s.get("label", "")).find("agradec") >= 0:
            outro_idx = i
            break
    if outro_idx is None and _looks_like_outro(sections[last_idx].get("text", ""),
                                               sections[last_idx].get("label", "")):
        outro_idx = last_idx

    used_ids = {s.get("id") for s in sections}
    if outro_idx is not None:
        outro = sections.pop(outro_idx)
        used_ids.discard(outro.get("id"))
        new_id = _unique_id(OUTRO_ID, used_ids)
        _set(outro, "id", new_id, changes, "outro")
        _set(outro, "label", OUTRO_LABEL, changes, new_id)
        _set(outro, "text", OUTRO_TEXT, changes, new_id)
        sections.append(outro)
        if outro_idx != last_idx:
            changes.append("agradecimento movido para o final")
    else:
        new_id = _unique_id(OUTRO_ID, used_ids)
        outro = {
            "id": new_id,
            "label": OUTRO_LABEL,
            "text": OUTRO_TEXT,
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

    first = sections[0]
    if first.get("id") != "s0":
        issues.append("a primeira secao deve ter id 's0'")
    intro_text = first.get("text", "")
    if not _INTRO_RE.match(intro_text):
        issues.append("s0 nao comeca com 'Oi, amiguinho! Tudo bem com você...'")
    if _BAD_OPEN_RE.match(intro_text):
        issues.append("s0 ainda comeca com cumprimento antigo ('Olá, família!')")
    if "hahaha" in _fold(intro_text):
        issues.append("s0 nao pode ter risada escrita")

    last = sections[-1]
    if last.get("id") != OUTRO_ID:
        issues.append("a ultima secao deve ter id '%s'" % OUTRO_ID)
    if _fold(last.get("label", "")) != _fold(OUTRO_LABEL):
        issues.append("a ultima secao deve ter label '%s'" % OUTRO_LABEL)
    if _fold(last.get("text", "")) != _fold(OUTRO_TEXT):
        issues.append("o texto do agradecimento nao confere com o contrato")

    ids = [s.get("id") for s in sections]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        issues.append("ids duplicados: %s" % ", ".join(dups))
    return issues
