# -*- coding: utf-8 -*-
"""
Gerador de prompt mestre do Videomaker (embutido na UI e no executor diario).

Sem dependencias e sem interface propria: a UI (pipeline_ui.py) e o
daily_runner.py importam este modulo. Ele substitui o antigo launcher
prompt.py (customtkinter), mantendo os mesmos parametros e o mesmo
"prompt mestre", e acrescenta:
  - autopreenchimento corrigido (palavras inteiras; "familia" nao vira "IA")
  - briefing compacto para a etapa de roteiro do pipeline
  - preset do canal "Frida e Luna" com a formula de sucesso
    (editavel em scripts/channel_style.txt)
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHANNEL_STYLE_FILE = HERE / "channel_style.txt"

GOALS = ["Educar", "Entreter", "Inspirar", "Vender", "Informar"]
CONTENT_TYPES = ["Documentário", "História", "Tecnologia", "IA", "Pets", "Infantil", "Curso", "Tutorial",
                 "Podcast", "Shorts", "Corporativo"]
DURATIONS = ["30 segundos", "1 minuto", "5 minutos", "10 minutos", "20 minutos"]
VISUAL_STYLES = ["Netflix Documentary", "National Geographic", "Animação 3D Cinematográfica", "Apple Keynote", "YouTube Moderno",
                 "Cartoon", "História Militar"]
VOICES = ["Automática", "Masculina", "Feminina", "Sem narração"]
COST_MODES = ["Economia Máxima", "Balanceado", "Qualidade Máxima"]
PRESETS = ["Nenhum", "Frida e Luna"]

DEFAULT_PARAMS = {
    "title": "", "theme": "", "goal": "Educar", "content_type": "Documentário", "duration": "10 minutos",
    "audience": "Geral / Adulto", "visual_style": "Netflix Documentary", "voice": "Automática",
    "cost_mode": "Economia Máxima", "reference": "", "preset": "Nenhum",
}

DEFAULT_CHANNEL_STYLE = """REGRAS DO CANAL "FRIDA E LUNA"
Protagonistas fixas (o mundo é visto do ponto de vista dos cachorros; sem humanos em cena):

LUNA (salsicha / dachshund fêmea):
- Salsicha fêmea, pelagem marrom-chocolate, pelo curto, liso e rente (padrão da raça).
- Tem uns 11 anos (aparência saudável, sem sinais exagerados de idade).
- Focinho coberto pelo mesmo pelo curto, com apenas alguns pelinhos brancos discretos no contorno.
- MUITO briguenta: late, reclama e cria caso por tudo.
- Muito apegada ao território da casa; não gosta de dividir atenção.
- Quem manda no par é ela: a chefona da casa, apesar dos ~10 kg.
- Pelo sempre curto e liso (visual liso, não wire-haired).
- Apelido carinhoso: Luninha (usar na narração com carinho, sem trocar o nome Luna).

FRIDA (buldogue inglesa fêmea):
- Buldogue inglesa fêmea grande (~30 kg), pelagem amarela-fawn (a cor clássica dos buldogues).
- Super tranquila, pacata e preguiçosa (e super gulosa).
- Obedece à Luna em TUDO: deseja agir, mas cede à chefona marrom.
- No fundo, as duas são amiguinhas.
- Apelido carinhoso: Fridóca (usar na narração com carinho, sem trocar o nome Frida).

FORMATO DAS SEÇÕES (REGRA CRÍTICA):
Cada seção deve conter APENAS o texto que o narrador vai falar em voz alta.
PROIBIDO colocar no texto das seções: ficha de personagens, descrição física,
prompt de imagem ou notas de estilo visual (ex.: "Luna: cadela dachshund...",
"Visual: animação 3D..."). Esses dados viram narração e estragam o vídeo.
A descrição dos personagens para as imagens é aplicada automaticamente depois,
fora do roteiro — você não precisa (e não deve) escrevê-la nas seções.

CONTRATO DE ABERTURA E ENCERRAMENTO (REGRA CRÍTICA):
A primeira seção (s0) começa SEMPRE com o cumprimento humanizado:
"Oi, amiguinho! Tudo bem com você? Que legal te ver por aqui! Hoje a gente vai
falar de <assunto do vídeo>." PROIBIDO começar com "Olá, família!" ou qualquer
cumprimento genérico. A última seção (s_outro, label "Agradecimento") é SEMPRE:
"Muito obrigado por assistir nossos vídeos, um beijo grande no seu coração,
fique com Deus e até a nossa próxima aventura, tchau tchau!!"
Essas duas seções fazem parte do roteiro (e das cenas, narração e timeline).

Fórmula de cada episódio:
0. APRESENTAÇÃO (seção s0, label "Apresentação do Canal"): o narrador começa
   SEMPRE com "Oi, amiguinho! Tudo bem com você? Que legal te ver por aqui!
   Hoje a gente vai falar de <assunto do vídeo>." e segue com uma frase curta
   e empolgada. Esta seção é curta (25 a 45 palavras) e vem ANTES do gancho.
1. GANCHO (0-10 s): logo após a apresentação, comece no meio da ação, com uma
   pergunta ou uma situação absurda.
2. PROMESSA (10-30 s): deixe claro o que vai acontecer e plante 2 ou 3 perguntas que só serão respondidas mais adiante (sem enganar o público).
3. DESENVOLVIMENTO: uma virada, piada visual ou mudança de cenário a cada 60-90 segundos. Ritmo ágil. Frida e Luna com objetivos diferentes, que se chocam.
4. DUAS CAMADAS: piadas físicas e visuais para as crianças + um toque de humor da vida real para os adultos (segunda-feira, dieta, preguiça, rotina da casa).
5. CLÍMAX E RESOLUÇÃO: responda todas as perguntas abertas e termine com uma surpresa.
6. FINAL: uma lição carinhosa em uma frase (amizade, paciência, honestidade) na
   última seção de história.
7. AGRADECIMENTO (seção final s_outro, label "Agradecimento"): encerre SEMPRE
   com o texto exato "Muito obrigado por assistir nossos vídeos, um beijo grande
   no seu coração, fique com Deus e até a nossa próxima aventura, tchau tchau!!".

Se o tema for informativo (curiosidade, raça, história real): os fatos devem ser corretos e simples, contados dentro de uma história com a Frida e a Luna como guias. Quando algo for lenda ou incerto, diga que é lenda.
Se o tema for uma saga em partes: comece lembrando em 1 frase o que já aconteceu e termine cada parte com um gancho para a próxima.

Proibido: animal em perigo ou sofrendo como atração; violência; sustos pesados; conselhos médicos ou veterinários específicos (diga apenas "converse com um veterinário"); repetir a mesma estrutura de piada de outros episódios; humor com estereótipos.
Tom: português do Brasil, caloroso e engraçado, para crianças e adultos, frases curtas."""


def channel_style():
    try:
        txt = CHANNEL_STYLE_FILE.read_text(encoding="utf-8").strip()
        if txt:
            return txt
    except Exception:
        pass
    return DEFAULT_CHANNEL_STYLE


# --------------------------------------------------------------- duracao ---
def duration_to_seconds(text, default=600):
    t = (text or "").lower()
    m = re.search(r"(\d+)\s*(?:min|minuto)", t)
    s = re.search(r"(\d+)\s*(?:s\b|seg)", t)
    total = 0
    if m:
        total += int(m.group(1)) * 60
    if s:
        total += int(s.group(1))
    return total or default


def seconds_to_duration(sec):
    sec = int(sec)
    if sec < 90:
        return "%d segundos" % sec
    minutes = int(round(sec / 60.0))
    return "1 minuto" if minutes == 1 else "%d minutos" % minutes


# ----------------------------------------------------------- autopreencher ---
def _has(text, words):
    return any(re.search(r"(?<!\w)%s(?!\w)" % re.escape(w), text) for w in words)


def autofill(theme):
    """Sugere parametros a partir do tema digitado. Retorna so os campos alterados."""
    t = (theme or "").lower().strip()
    if not t:
        return {}
    if _has(t, ["pet", "pets", "cachorro", "cachorros", "cão", "cães", "cao", "caes", "gato", "gatos", "animal",
                "animais", "salsicha", "bulldog", "buldogue", "vira-lata", "filhote", "frida", "luna"]):
        return dict(content_type="Pets", visual_style="Animação 3D Cinematográfica", goal="Entreter", voice="Feminina",
                    audience="Família (crianças e adultos)", preset="Frida e Luna")
    if _has(t, ["guerra", "batalha", "militar", "tercios", "exército", "segunda guerra"]):
        return dict(content_type="História", visual_style="História Militar", goal="Informar",
                    audience="Adulto / Acadêmico", preset="Nenhum")
    if _has(t, ["ia", "inteligência artificial", "tecnologia", "software", "python", "oracle", "database", "dba"]):
        return dict(content_type="IA" if _has(t, ["ia", "inteligência artificial"]) else "Tecnologia",
                    visual_style="Apple Keynote", goal="Educar", audience="Profissionais / Desenvolvedores",
                    preset="Nenhum")
    if _has(t, ["infantil", "criança", "crianças", "kids", "desenho"]):
        return dict(content_type="Infantil", visual_style="Cartoon", goal="Entreter",
                    audience="Infantil (Crianças)", preset="Nenhum")
    if _has(t, ["história", "historia", "documentário", "documentario"]):
        return dict(content_type="História", visual_style="Netflix Documentary", goal="Educar",
                    audience="Geral / Adulto", preset="Nenhum")
    return dict(content_type="Documentário", visual_style="Netflix Documentary", goal="Educar",
                audience="Geral / Adulto", preset="Nenhum")


# --------------------------------------------------------------- estrategia ---
def detect_pipeline(content_type):
    return {"Documentário": "documentary-montage", "História": "documentary-montage", "Tecnologia": "explainer",
            "IA": "explainer", "Pets": "explainer", "Infantil": "animation", "Curso": "explainer",
            "Tutorial": "explainer", "Podcast": "podcast-repurpose", "Shorts": "clip-factory",
            "Corporativo": "explainer"}.get(content_type, "explainer")


def runtime_strategy(cost_mode):
    base = {"runtime": "HyperFrames", "images": "Gemini Media Scraping", "music": "Gemini Media Scraping"}
    tts = {"Economia Máxima": "Edge-TTS", "Balanceado": "Azure"}.get(cost_mode, "ElevenLabs")
    return dict(base, tts=tts)


def recommendation_text(p):
    st = runtime_strategy(p["cost_mode"])
    lines = ["Pipeline: %s" % detect_pipeline(p["content_type"]), "-" * 30,
             "Runtime: %s" % st["runtime"], "Imagens: %s" % st["images"], "TTS: %s" % st["tts"],
             "Música: %s" % st["music"], "-" * 30, "Tipo: %s" % p["content_type"]]
    if p.get("preset", "Nenhum") != "Nenhum":
        lines.append("Preset do canal: %s" % p["preset"])
    return "\n".join(lines)


def _fill(p):
    q = dict(DEFAULT_PARAMS)
    q.update({k: v for k, v in (p or {}).items() if v is not None})
    q["theme"] = (q["theme"] or "").strip() or "Geral"
    q["title"] = (q["title"] or "").strip() or q["theme"][:60] or "Projeto Videomaker"
    return q


# ------------------------------------------------------------------ prompts ---
def build_master_prompt(p):
    """Prompt mestre completo (o mesmo do antigo prompt.py), para copiar/salvar."""
    q = _fill(p)
    st = runtime_strategy(q["cost_mode"])
    out = f"""Crie um vídeo cinematográfico e estruturado.

TÍTULO:
{q['title']}

ASSUNTO / TEMA CENTRAL:
{q['theme']}

OBJETIVO:
{q['goal']}

PÚBLICO-ALVO:
{q['audience']}

DURAÇÃO ESTIMADA:
{q['duration']}

TIPO DE CONTEÚDO:
{q['content_type']}

ESTILO VISUAL & PALETA:
{q['visual_style']}

NARRAÇÃO E TOM DE VOZ:
{q['voice']}

PIPELINE DE EXECUÇÃO:
{detect_pipeline(q['content_type'])}

------------------------------------------------

DIRETRIZES DE PRODUÇÃO POR ATOS (STORYTELLING):
1. Ato 1 (Hook & Introdução): Gancho forte nos primeiros segundos e contextualização do tema.
2. Ato 2 (Desenvolvimento): Aprofundamento dos fatos, evidências e dinâmica visual rica.
3. Ato 3 (Clímax & Conclusão): Reflexão final, encerramento imersivo e Chamada para Ação (CTA).

------------------------------------------------

POLÍTICA DE CUSTO E RECURSOS:
- Priorizar assets existentes, Python, Gemini Media Scraping e HyperFrames.
- Nunca utilizar serviços pagos sem aprovação prévia.

------------------------------------------------

RENDERIZAÇÃO E AUDITORIA:
- Runtime recomendado: {st['runtime']}
- Motor de Narração: {st['tts']}
- Executar auditoria rigorosa de ritmo, trilha sonora, transições e retenção antes da exportação final.
"""
    if q["preset"] != "Nenhum":
        out += "\n------------------------------------------------\n" + channel_style() + "\n"
    if (q["reference"] or "").strip():
        out += f"""
------------------------------------------------
VÍDEO DE REFERÊNCIA PARA ANÁLISE:
{q['reference'].strip()}
Aplicar fluxo video-reference-analyst para inspirar a estrutura sem copiar conteúdo diretamente.
"""
    return out


def build_script_brief(p):
    """Briefing compacto enviado a etapa de roteiro do pipeline (sem a parte de infraestrutura)."""
    q = _fill(p)
    out = f"""Escreva o ROTEIRO (apenas texto) de um episódio animado para o YouTube.
Você não cria vídeo nem imagem: esta etapa produz somente o texto do roteiro.

TÍTULO: {q['title']}
TEMA: {q['theme']}
OBJETIVO: {q['goal']}
PÚBLICO-ALVO: {q['audience']}
DURAÇÃO: cerca de {q['duration']}
TIPO DE CONTEÚDO: {q['content_type']}
ESTILO VISUAL: {q['visual_style']}
NARRAÇÃO: {q['voice']}

ESTRUTURA EM 3 ATOS:
1. Gancho forte nos primeiros 10 segundos e contexto.
2. Desenvolvimento com viradas e mudanças de cena frequentes.
3. Clímax, lição final e chamada para ação (CTA).
"""
    if q["preset"] != "Nenhum":
        out += "\n" + channel_style() + "\n"
    if (q["reference"] or "").strip():
        out += "\nREFERÊNCIA (inspirar a estrutura, sem copiar): %s\n" % q["reference"].strip()
    return out.strip()


def episode_params(topic, duration_s=590, overrides=None):
    """Parametros padrao dos episodios do canal Frida e Luna (usado pelo executor diario)."""
    p = dict(DEFAULT_PARAMS, title=topic, theme=topic, goal="Entreter", content_type="Pets",
             duration=seconds_to_duration(duration_s), audience="Família (crianças e adultos)",
             visual_style="Animação 3D Cinematográfica", voice="Feminina", cost_mode="Economia Máxima", preset="Frida e Luna")
    p.update(overrides or {})
    return p
