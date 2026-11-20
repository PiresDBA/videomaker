# -*- coding: utf-8 -*-
"""voz_nativa.py — fonte única da verdade da narração (REGRA 2026-11-20).

REGRA DO USUÁRIO (reforçada 2026-11-20):
  1. "O modelo da voz tem que ser do país do vídeo a ser gerado."
  2. "Todos com voz infantil e com emoção ao máximo."

Motivo do bug que gerou o retrabalho: o pipeline usava VoiceCraft -> provider
'auto' -> Gemini TTS (vozes Kore/Achernar/Leda). Essas vozes são as MESMAS para
pt/en/es (não são atreladas a nenhum país). Com o perfil 'infantil' (prompt em
português) o modelo narrava inglês/espanhol com SOTAQUE BRASILEIRO:
o vídeo EN saiu com narração de brasileira e o ES com sotaque PT no meio.

Solução: nvidia Magpie Multilingual — voz ATRELADA AO PAÍS no próprio ID da
voz, com VARIAÇÃO DE EMOÇÃO (`.Happy`, `.PleasantSurprised`) e perfil infantil.
Testado em 2026-11-20 com Whisper: pt=0.99, en=0.99, es=0.98 de probabilidade
de idioma correto (nativo), com entoação alegre/infantil.

  pt -> pt-BR -> Magpie-Multilingual.PT-BR.Louise   + perfil infantil
  en -> en-US -> Magpie-Multilingual.EN-US.Jason.Happy (emoção máxima)
  es -> es-ES -> Magpie-Multilingual.ES-US.Isabela.Happy (emoção máxima)

Gemini/auto/Kore/Aoede/Achernar/Leda são PROIBIDOS: voz sem país.
O Edge-TTS é o fallback (também nativo por país, mas sem controle de emoção).

Uso:
    from voz_nativa import VOZES_NATIVAS, voz_para, validar_voz, registrar_voz
    cfg = voz_para("en")   # -> dict com provider/voice/profile/rate/pitch
    validar_voz("en", "nvidia", "Magpie-Multilingual.EN-US.Jason.Happy")
    registrar_voz(proj, "en", "nvidia", "Magpie-Multilingual.EN-US.Jason.Happy")
"""
from __future__ import annotations
import json
from pathlib import Path

# Vozes com PAÍS no ID + emoção máxima + perfil infantil.
# 'profile=infantil' injeta a instrução de voz infantil (a API aplica o perfil
# mesmo no nvidia — testado). As variações .Happy/.PleasantSurprised dão a
# emoção máxima sem depender de SSML (que o Edge lê como jargão falado).
VOZES_NATIVAS = {
    "pt": {
        "pais": "pt-BR", "provider": "nvidia",
        "voice": "Magpie-Multilingual.PT-BR.Louise",
        "profile": "infantil", "rate": "+6%", "pitch": "+12Hz",
        "narrador": "Louise (brasileira, infantil)",
    },
    "en": {
        "pais": "en-US", "provider": "nvidia",
        "voice": "Magpie-Multilingual.EN-US.Jason.Happy",
        "profile": "infantil", "rate": "+4%", "pitch": "+8Hz",
        "narrador": "Jason (americano, infantil, feliz)",
    },
    "es": {
        "pais": "es-ES", "provider": "nvidia",
        "voice": "Magpie-Multilingual.ES-US.Isabela.Happy",
        "profile": "infantil", "rate": "+4%", "pitch": "+8Hz",
        "narrador": "Isabela (espanhola, infantil, feliz)",
    },
}

# Fallback Edge (nativo por país, porém sem controle de emoção real).
FALLBACK_EDGE = {
    "pt": "pt-BR-ThalitaNeural",
    "en": "en-US-AriaNeural",
    "es": "es-ES-ElviraNeural",
}

# Provedores/vozes sem país — proibidos na narração dos vídeos.
PROVEDORES_SEM_PAIS = ("gemini", "auto", "gcloud-chirp-sem-pais")
VOZES_SEM_PAIS = ("kore", "aoede", "achernar", "leda", "puck", "charon",
                  "fenrir", "orus", "zephyr")

# Prefixo exigido no ID da voz, por idioma (o país tem que estar no ID).
PREFIXO_PAIS = {"pt": "pt-", "en": "en-", "es": "es-"}
# Para nvidia o país vem no formato PT-BR / EN-US / ES-US dentro do ID.
PREFIXO_PAIS_NVIDIA = {"pt": "PT-BR.", "en": "EN-US.", "es": "ES-US."}


def voz_para(lang: str) -> dict:
    """Configuração de voz nativa do país para o idioma."""
    return dict(VOZES_NATIVAS.get(lang.strip().lower(), VOZES_NATIVAS["pt"]))


def validar_voz(lang: str, provider: str, voice: str) -> None:
    """Levanta ValueError se a voz/provedor não for nativa do país do vídeo.

    Chamado antes de sintetizar — se passar voz errada o erro aparece na hora,
    não depois de 35 minutos de render (foi o que aconteceu em 2026-11-20).
    """
    lang = lang.strip().lower()
    prov = (provider or "").strip().lower()
    voz = (voice or "").strip()
    cfg = VOZES_NATIVAS.get(lang)
    if not cfg:
        raise ValueError(f"Idioma não suportado para voz nativa: {lang!r}")
    if prov in PROVEDORES_SEM_PAIS:
        raise ValueError(
            f"VOZ SEM PAÍS PROIBIDA: provider '{prov}' narra {lang.upper()} "
            f"com sotaque de outro país (bug 2026-11-20). "
            f"Use provider='{cfg['provider']}' com voz '{cfg['voice']}'."
        )
    voz_lower = voz.lower()
    if any(voz_lower == v or voz_lower.startswith(v + "-") for v in VOZES_SEM_PAIS):
        raise ValueError(
            f"VOZ SEM PAÍS PROIBIDA: '{voz}' é a mesma locutora para todos os "
            f"idiomas. Use '{cfg['voice']}' ({cfg['pais']})."
        )
    if not voz_lower.startswith(PREFIXO_PAIS[lang]) and \
       not ("magpie" in voz_lower and PREFIXO_PAIS_NVIDIA[lang].lower() in voz_lower):
        raise ValueError(
            f"VOZ DO PAÍS ERRADO: '{voz}' não é nativa de {lang.upper()} "
            f"(esperado: '{cfg['voice']}')."
        )


def registrar_voz(proj: Path | str, lang: str, provider: str, voice: str) -> Path:
    """Grava trilha de auditoria da voz usada, para o Hook conferir depois."""
    lang = lang.strip().lower()
    validar_voz(lang, provider, voice)
    cfg = voz_para(lang)
    proj = Path(proj)
    art = proj / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    out = art / f"narracao_voz_nativa_{lang}.json"
    out.write_text(json.dumps({
        "lang": lang,
        "pais": cfg["pais"],
        "provider": provider,
        "voice": voice,
        "profile": cfg["profile"],
        "rate": cfg["rate"],
        "pitch": cfg["pitch"],
        "narrador": cfg["narrador"],
        "regra": "modelo de voz do pais do video + voz infantil + emocao maxima (2026-11-20)",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def conferir_voz_gravada(proj: Path | str, lang: str) -> str | None:
    """Retorna erro se o registro de voz nativa estiver ausente/inválido."""
    lang = lang.strip().lower()
    f = Path(proj) / "artifacts" / f"narracao_voz_nativa_{lang}.json"
    if not f.exists():
        return (f"REGISTRO DE VOZ NATIVA ausente para {lang.upper()}: "
                f"rode a narração com voz_nativa.py")
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        validar_voz(lang, d.get("provider", ""), d.get("voice", ""))
        if str(d.get("profile", "")).lower() != "infantil":
            return f"VOZ {lang.upper()} sem perfil infantil (exigido pelo usuário)"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"registro de voz nativa ilegível: {e}"
    return None
