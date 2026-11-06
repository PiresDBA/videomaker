# -*- coding: utf-8 -*-
"""
Gera scenes.json + image_prompts.json a partir de artifacts/script.json.

E deterministico: nao chama IA. Para cada secao cria uma imagem principal
(sN_scene.jpg) com um prompt derivado do texto da secao, no vocabulario
seguro de "animação 3D cinematográfica" (SEM nomes de estúdios/marcas, que
acionam filtros de IP no provedor de imagem).

Quando o roteiro e sobre Frida e Luna (preset do canal), todos os prompts de
imagem comecam com a descricao fixa dos personagens (FRIDA_LUNA_DESC) para
garantir consistencia visual entre as cenas.

Regras anti-rejeicao (Gemini image):
  - zero nomes de estudio/marcas (Pixar, Disney, Ghibli, DreamWorks...)
  - zero "in the style of" / "inspirado nas animações da X e Y"
  - ficha de personagens CURTA, visual, sem "possessiva", "tutor", "QUEM MANDA"
  - sem Hahaha/risadas escritas na cena (energia fica na narracao)
  - sem HTML; estilo aparece UMA vez; prompt capado em MAX_PROMPT_CHARS

Uso:
  python scripts/generate_scenes_and_prompts.py --script artifacts/script.json \
      --scenes-out scripts/scenes.json --prompts-out artifacts/image_prompts.json
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent

MAX_PROMPT_CHARS = 1400


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def reference_image_path():
    """Caminho da imagem de referencia global (banco de imagens), se existir."""
    try:
        cfg = load_json(HERE / "config.json")
        p = Path(cfg.get("reference_image", ""))
        if p and p.is_absolute() and p.exists():
            return str(p)
    except Exception:
        pass
    return ""


def slugify(t):
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return re.sub(r"_+", "_", t).strip("_")


def clean_text(t):
    t = t.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", t).strip()


# Vocabulario seguro de estilo (SEM marcas de estudio/artistas).
SAFE_STYLE = (
    "high-quality cinematic 3D animation, fictional cartoon characters in a fantasy world, "
    "stylized feature-length family animation look, "
    "stylized expressive characters, professional lighting and composition, "
    "soft cinematic lighting, shallow depth of field, not real animals, not real people, "
    "no text, no subtitles, no captions, no speech bubbles, no watermarks, no letters, no words, no typography"
)

# Ficha visual CURTA por imagem. Cada prompt gera UMA imagem.
# Tudo é PERSONAGEM FICTÍCIO de desenho animado em mundo de fantasia —
# não animal real, não raça "de verdade", não pessoa. O Gemini rejeita
# prompts que parecem pedir a foto de um animal/indivíduo que existe.
FRIDA_LUNA_DESC = (
    "Personagens fictícias de desenho animado em um mundo de fantasia "
    "(não são animais reais). "
    "Luna: personagem de salsicha de cartoon, pelo curto liso marrom-chocolate, "
    "focinho curto com pelinhos brancos discretos, corpo alongado, patas curtas, "
    "orelhas caídas. Pequena, expressiva, mandona e energética. "
    "Apelido carinhoso: Luninha. "
    "Frida: personagem de buldogue de cartoon, grande, pelagem fawn amarelada, "
    "porte robusto e rugas suaves. Calma, preguiçosa e dócil. "
    "Apelido carinhoso: Fridóca. "
    "Contraste: Luna lidera; Frida acompanha em tranquilidade. "
    "Cenário lúdico de fantasia visto do ponto de vista dos cães, sem pessoas. "
    "Nenhuma letra, legenda, balão de fala ou marca-d'água na imagem. "
)

# Estudios/marcas que o filtro de IP bloqueia (mesmo parciais).
STUDIO_WORDS = (
    "pixar", "disney", "ghibli", "dreamworks", "illumination",
    "sony pictures", "warner", "marvel", "dc comics", "pixar/disney",
    "disney/pixar", "in the style of", "estilo pixar", "estilo disney",
)

LAUGH_RE = re.compile(
    r"\b(?:hahaha+|ha\s+ha\s+ha+|haha+|kkkk+|rsrs+|jajaja+|hihi+|huehue+)\b[!.]*",
    re.I,
)


def strip_html(text):
    return re.sub(r"<[^>]+>", " ", str(text))


def sanitize_style(style):
    """Remove estudios, conectivos órfãos ('da  e ,'), HTML e redundância."""
    s = strip_html(style)
    s = clean_text(s)
    # marcas
    for w in STUDIO_WORDS:
        s = re.sub(re.escape(w), " ", s, flags=re.I)
    # "inspirado nas animações da X e Y" / "in the style of"
    s = re.sub(
        r"inspirad[oa]s?\s+(?:nas?|no[s]?|em)\s+anima[cç][õo]es\s*(?:da|do|das|dos)?\s*(?:e|,|;)?",
        " ", s, flags=re.I,
    )
    s = re.sub(r"in the style of|estilo (de|do|da|dos|das)\s*", " ", s, flags=re.I)
    # conectivos órfãos: "da  e ,", "do ,", "das e"
    s = re.sub(r"\b(?:da|do|das|dos|de|em|no|na)\s+(?:e|,|;)\s*", " ", s, flags=re.I)
    s = re.sub(r"\b(?:da|do|das|dos|de)\s*$", "", s, flags=re.I)
    # pontuação órfã
    s = re.sub(r"\s+([,.;;])", r"\1", s)
    s = re.sub(r",{2,}", ",", s)
    s = re.sub(r";{2,}", ";", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = s.strip(" ,;.")
    # frases vazias que sobraram
    s = re.sub(r"anima[cç][õo]es\s*(?:da|do|das|dos)?\s*(?:e|,|;|$)", " ", s, flags=re.I)
    s = re.sub(r"estilo visual 3d\s*(?:e|,|;|$)", " ", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,;.")
    return s


def _clean_scene_text(text, limit=400):
    """Limpa e trunca o texto da cena de forma segura:
    - remove tags HTML;
    - remove risadas escritas (Hahaha) que nao ajudam a imagem;
    - colapsa espacos;
    - corta em <= limit sempre em limite de frase ou palavra (nunca no meio)."""
    text = strip_html(text)
    text = LAUGH_RE.sub(" ", text)
    text = re.sub(r"\(\s*\)", " ", text)  # parenteses orfaos das risadas
    text = clean_text(text)
    if len(text) <= limit:
        return text
    slice_ = text[:limit]
    # corte no fim de frase mais proximo do limite
    m = max((p for p in re.finditer(r"[.!?](?=\s|$)", slice_)), key=lambda z: z.end(), default=None)
    if m and m.end() >= int(limit * 0.5):
        return slice_[: m.end()].strip()
    cut = slice_.rstrip()
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.strip()


def is_frida_luna_script(script):
    """Detecta se o roteiro usa o preset Frida e Luna."""
    preset = script.get("preset", "")
    content_type = script.get("content_type", "")
    style = script.get("style_notes", "")
    title = script.get("title", "")
    texto = " ".join([preset, content_type, style, title]).lower()
    # Tambem escaneia os textos das secoes, pois o script.json gerado pela IA
    # pode nao reter os campos preset/content_type.
    for sec in script.get("sections", []):
        texto += " " + sec.get("text", "").lower()
        texto += " " + sec.get("label", "").lower()
    return ("frida" in texto or "luna" in texto or
            "bulldog" in texto or "buldogue" in texto or
            "salsicha" in texto or "dachshund" in texto)


def fix_species(text):
    """No preset Frida e Luna as duas sao personagens de cartoon (nao animais
    reais). O roteiro as vezes chama a Frida de gatinha ou coloca a vovo
    (humana) em cena — ambos confundem o modelo de imagem."""
    text = re.sub(r"\bgatinha\s+Frida\b", "Frida", text, flags=re.I)
    text = re.sub(r"\bFrida\s*,?\s*a? gatinha\b", "Frida", text, flags=re.I)
    text = re.sub(r"\bcarreira felina\b", "carreira", text, flags=re.I)
    text = re.sub(r"\bgatinh[oa]s?\b", "cachorrinha", text, flags=re.I)
    text = re.sub(r"\bgatinha\b", "cachorrinha", text, flags=re.I)
    text = re.sub(r"\bgatinho\b", "cachorro", text, flags=re.I)
    text = re.sub(r"\bgatos\b", "cachorros", text, flags=re.I)
    text = re.sub(r"\bgata\b", "cadela de cartoon", text, flags=re.I)
    text = re.sub(r"\bgato\b", "cachorro de cartoon", text, flags=re.I)
    # humanos fora do mundo dos caes
    text = re.sub(r"\b[Aa] vov[oó]\b", "A cadela mais velha da casa", text)
    text = re.sub(r"\bvov[oó]\b", "cadela mais velha", text, flags=re.I)
    text = re.sub(r"\b(avó|vó)\b", "cadela mais velha", text, flags=re.I)
    text = re.sub(r"\b(dono|dona|tutor|tutora|senhor|senhora)\b", "personagem de cartoon", text, flags=re.I)
    text = re.sub(r"\s{2,}", " ", text)
    return text


REF_CHARS = (
    "PERSONAGENS E ESTILO: siga a imagem de referência anexada para TUDO — "
    "aparência, cores e traço das personagens (Luna: dachshund marrom pequena; "
    "Frida: buldogue fawn grande) e o estilo visual geral. "
    "Desenho animado original e lúdico, estilo visual próprio "
    "(não copie outros desenhos, filmes ou marcas existentes), "
    "visto do ponto de vista dos cães, sem humanos."
)


# Suavizacao anti-recusa do filtro do provedor (nao muda a narracao/TTS).
SOFTEN_MAP = (
    ("caos absoluto", "caos divertido"),
    ("caos complet", "caos divertido"),
    ("gritando", "latindo bem alto"),
    ("grimar", "reclamar"),
    ("olhou feio", "deu uma olhada indiferente"),
    ("olha feia", "olhada indiferente"),
    ("exige respeito imediato", "pede cuidado"),
    
    ("temido", "famoso"),
    ("desespero", "ansiedade cômica"),
    ("sargento estrito", "capitã animada"),
    ("privado de tudo", "querido por todos"),
    (" ORDENS EM ", " CONVERSA EM "),
)


def soften_terms(text):
    for a, b in SOFTEN_MAP:
        text = text.replace(a, b)
        text = text.replace(a.capitalize(), b.capitalize())
        text = text.replace(a.upper(), b.upper())
    return text


def build_prompt(title, scene_text, style_clean, frida_luna, has_reference=False, variant="a"):
    """Monta o prompt curto, sem redundancia e sem marcas.
    Cada prompt gera UMA imagem. variant 'a' = cena principal; 'b' = close-up
    / reacao dos personagens (segunda imagem da mesma cena, para engajamento).
    A CENA vem primeiro (o modelo focava só nos
    personagens quando a ficha abria o prompt); personagens ficam para depois,
    amarrados a imagem de referencia quando ela existe."""
    if frida_luna:
        scene_text = fix_species(scene_text or "")
    scene = soften_terms(scene_text or "cena ilustrativa da história")
    if variant == "b":
        scene = (scene + " Foco nos rostos e nas caretas engraçadas dos personagens.").strip()
    # A cena descreve a ACAO. Anti-texto vai no bloco final (em PT): baloes
    # com escrita aparecerem mesmo com SAFE_STYLE em ingles no fim do prompt.
    parts = ["CENA (gere exatamente esta cena): %s" % scene]
    if frida_luna:
        if has_reference:
            parts.append(REF_CHARS)
        else:
            parts.append(FRIDA_LUNA_DESC.strip())
    parts.append(
        "Uma única imagem estática (NÃO gere vídeo, NÃO gere áudio). "
        "NÃO escreva NADA na imagem: sem palavras, letras, números, legendas, "
        "onomatopeias, balões de fala ou balões de pensamento. "
        "Sem logotipos ou marcas visíveis."
    )
    prompt = "\n".join(parts)
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS]
        # corta em fim de linha
        if "\n" in prompt:
            prompt = prompt[: prompt.rfind("\n")]
        prompt = prompt.rstrip(" ,;.")
    return prompt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(PROJECT / "artifacts" / "script.json"))
    ap.add_argument("--scenes-out", default=str(HERE / "scenes.json"))
    ap.add_argument("--prompts-out", default=str(PROJECT / "artifacts" / "image_prompts.json"))
    args = ap.parse_args()

    script = load_json(args.script)
    sections = script.get("sections", [])
    style = script.get("style_notes", "")
    style = sanitize_style(style)
    title = clean_text(script.get("title", "video explicativo"))
    frida_luna = is_frida_luna_script(script)

    scenes = {"_help": "Para cada secao: images = arquivos em assets/images/. split = fracao da cena em que entra a 2a imagem. camera = [escala_inicial, escala_final, x_inicial, x_final, y_inicial, y_final] por imagem. Sem camera = push-in padrao."}
    prompts = {}
    default_camera = [[1.03, 1.10, 0, 18, 0, -8]]

    for i, s in enumerate(sections):
        sid = s.get("id", "s%d" % i)
        text = _clean_scene_text(s.get("text", ""))
        label = s.get("label", sid)
        base = slugify(label) or sid
        scene_name = "%s_scene" % base
        has_ref = bool(reference_image_path())
        if sid == "s0":
            # Capa: unica imagem de apresentacao
            prompts[scene_name] = build_prompt(title, text, style, frida_luna, has_reference=has_ref, variant="a")
            scenes[sid] = {
                "images": ["%s.jpg" % scene_name],
                "split": None,
                "camera": default_camera,
            }
        else:
            # Duas imagens por secao: cena principal + close-up/reacao dos personagens
            prompts[scene_name] = build_prompt(title, text, style, frida_luna, has_reference=has_ref, variant="a")
            prompts[scene_name + "_b"] = build_prompt(title, text, style, frida_luna, has_reference=has_ref, variant="b")
            scenes[sid] = {
                "images": ["%s.jpg" % scene_name, "%s_b.jpg" % scene_name],
                "split": 0.5,
                "camera": [
                    [1.03, 1.10, 0, 18, 0, -8],
                    [1.06, 1.14, 10, -10, 5, 5],
                ],
            }

    Path(args.scenes_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.scenes_out, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)
    Path(args.prompts_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.prompts_out, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)
    print("cenas:", len(sections), "| imagens:", len(prompts), "| frida_luna:", frida_luna)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
