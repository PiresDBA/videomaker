import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  Play, Calendar, Send, Settings, Video, Upload, X, Eye, Zap, List,
  RefreshCw, Film, Sparkles, Moon, Sun, Menu, ChevronLeft, ChevronRight,
  Download, Edit2, Clipboard, RotateCw, HardDrive, Mic, Layout, FolderSearch,
  Image as ImageIcon, Terminal, TestTube, ArrowRight, CheckCircle, Trash2,
  Clock, FileText, Monitor, Gauge, Activity, TrendingUp, BarChart3, Loader2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useLogsBus, useRunBus, RunBusProvider, isLive, phaseLabel } from "./hooks/useRunBus";
import { api } from "./services/api";
import { fmtDuration } from "./utils/fmt";
import { KpiTile } from "./components/KpiTile";
import { PhaseGauge, Waterfall, Sparkline, LogHistogram } from "./components/execWidgets";
import { PHASES, PHASE_KEYS, PHASE_NAME } from "./utils/phases";
import { Section, Btn, Switch, Field, FilePicker, Statusline } from "./components/ui";
import { PipelineRail } from "./components/PipelineRail";


const PAGES = [
  { key: "create", label: "Criar", icon: Sparkles },
  { key: "publish", label: "Publicar", icon: Send },
  { key: "daily", label: "Di�rio", icon: Calendar },
  { key: "tests", label: "Testes", icon: TestTube },
  { key: "activity", label: "Atividade", icon: Terminal },
  { key: "executivo", label: "Executivo", icon: Gauge },
  { key: "settings", label: "Ajustes", icon: Settings },
];

const PAGE_TITLES = {
  create: "Criar V�deo",
  publish: "Publicar no YouTube",
  daily: "Di�rio & Agendamento",
  tests: "Testes de Pipeline",
  activity: "Atividade & Observabilidade",
  executivo: "Painel Executivo",
  settings: "Ajustes",
};


const RUN_MODES = [
  { key: "auto", label: "Autom�tico", desc: "Retoma dos checkpoints e segue at� o render" },
  { key: "from", label: "A partir de", desc: "Executa de uma fase at� o final" },
  { key: "only", label: "Somente", desc: "Executa apenas as fases escolhidas" },
  { key: "skip", label: "Pular", desc: "Executa tudo, exceto as fases marcadas" },
];
const YT_MODES = [
  { key: "manual", label: "Manual" },
  { key: "auto", label: "Autom�tico" },
  { key: "ask", label: "Perguntar" },
];
const YT_PRIVACY = [
  { key: "private", label: "Privado" },
  { key: "unlisted", label: "N�o listado" },
  { key: "public", label: "P�blico" },
];
const VOICES = [
  "pt-BR-ThalitaNeural", "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural",
  "en-US-AriaNeural", "en-US-GuyNeural",
];
const RECURRENCE_OPTS = [
  { val: "none", label: "N�o repetir" },
  { val: "daily", label: "Todos os dias" },
  { val: "weekdays", label: "Dias �teis" },
  { val: "weekly", label: "Semanal" },
];
const DURATION_PRESETS = [
  { label: "3 min", secs: 180 },
  { label: "5 min", secs: 300 },
  { label: "10 min", secs: 590 },
  { label: "15 min", secs: 900 },
];
const ZOOM_LEVELS = [75, 100, 125, 150];

const iso = (d) =>
  d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");

const slugify = (t) => {
  if (!t) return "�";
  return t.toLowerCase().replace(/[^a-z0-9\s-]/gi, "").trim().replace(/\s+/g, "-").slice(0, 40) || "projeto";
};

// ============================================================================
// BASE COMPONENTS
// ============================================================================


// ============================================================================
// PAGE: CREATE
// ============================================================================

const PageCreate = ({ onRun, onFatal, running, runId, slug, setSlug, toast, runRequest }) => {
  const { attach, run: liveRun } = useRunBus();
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("auto");
  const [fromPhase, setFromPhase] = useState("script");
  const [onlyPhases, setOnlyPhases] = useState(new Set());
  const [skipPhases, setSkipPhases] = useState(new Set());
  const [force, setForce] = useState(false);
  const [noParallel, setNoParallel] = useState(false);
  const [skipCheck, setSkipCheck] = useState(false);
  const [upload, setUpload] = useState(false);
  const [ytVideoId, setYtVideoId] = useState("");
  const [ytThumbFile, setYtThumbFile] = useState(null);
  const [ytSecretFile, setYtSecretFile] = useState(null);
  const [ytTitle, setYtTitle] = useState("");
  const [ytDesc, setYtDesc] = useState("");
  const [ytTags, setYtTags] = useState("");
  const [voice, setVoice] = useState(VOICES[0]);
  const [rate, setRate] = useState("+12%");
  const [pitch, setPitch] = useState("+8Hz");
  const [style, setStyle] = useState("excited");
  const [wait, setWait] = useState("240");
  const [duration, setDuration] = useState(590);
  const [plan, setPlan] = useState([]);
  const [doneSet, setDoneSet] = useState(new Set());
  const [slugExists, setSlugExists] = useState(false);

  useEffect(() => setSlug(slugify(prompt)), [prompt]);

  useEffect(() => {
    if (!slug) { setSlugExists(false); return; }
    let on = true;
    api.projectStatus(slug)
      .then(() => { if (on) setSlugExists(true); })
      .catch(() => { if (on) setSlugExists(false); });
    return () => { on = false; };
  }, [slug]);

  // Load pipeline defaults from settings on mount
  useEffect(() => {
    const loadDefaults = async () => {
      try {
        const data = await api.getSettings();
        const p = data.pipeline || {};
        setDuration(p.duration ?? 590);
        setVoice(p.voice ?? "pt-BR-ThalitaNeural");
        setRate(p.rate ?? "+12%");
        setPitch(p.pitch ?? "+8Hz");
        setNoParallel(p.no_parallel ?? false);
        setSkipCheck(p.skip_check ?? false);
        setUpload(p.publish ?? false);
      } catch (e) {
        // Silently ignore if backend not available
      }
    };
    loadDefaults();
  }, []);

  const phasesArg = () => {
    if (mode === "only") return [...onlyPhases].join(",") || undefined;
    if (mode === "skip") return [...skipPhases].join(",") || undefined;
    return undefined;
  };

  const handleRun = useCallback(async () => {
    if (!prompt.trim()) {
      toast("Descreva o tema do v�deo antes de gerar.", "warn");
      return;
    }
    try {
      const res = await api.runPipeline({
        prompt, mode,
        phases: phasesArg(),
        from_phase: mode === "from" ? fromPhase : undefined,
        force, no_parallel: noParallel, skip_check: skipCheck,
        voice, rate, pitch, style, wait, duration,
        upload,
        yt_video_id: ytVideoId,
        yt_thumb: (ytThumbFile && ytThumbFile.path) || "",
        yt_secret: (ytSecretFile && ytSecretFile.path) || "",
        yt_title: ytTitle,
        yt_desc: ytDesc,
        yt_tags: ytTags,
      });
      setPlan(res.plan || PHASE_KEYS);
      attach(res.run_id, { slug, prompt, source: "create" });
      onRun(res.run_id);
      toast("Pipeline iniciado � run " + res.run_id, "ok");
    } catch (e) {
      onFatal("Erro ao iniciar pipeline: " + e.message);
    }
  }, [prompt, mode, onlyPhases, skipPhases, fromPhase, force, noParallel, skipCheck,
      voice, rate, pitch, style, wait, duration, upload, attach, slug,
      ytVideoId, ytThumbFile, ytSecretFile, ytTitle, ytDesc, ytTags]);

  useEffect(() => {
    if (runRequest && runRequest.type === "run") handleRun();
  }, [runRequest]);

  const togglePhase = (key) => {
    if (mode === "only") {
      const next = new Set(onlyPhases);
      next.has(key) ? next.delete(key) : next.add(key);
      setOnlyPhases(next);
    } else {
      const next = new Set(skipPhases);
      next.has(key) ? next.delete(key) : next.add(key);
      setSkipPhases(next);
    }
  };

  const summary = () => {
    const fromIdx = PHASE_KEYS.indexOf(fromPhase);
    if (mode === "auto") return "Checkpoints existentes s�o respeitados e o pipeline segue at� o render.";
    if (mode === "from") return `Executa de ${PHASE_NAME[fromPhase]} at� Render � ${PHASES.length - fromIdx} etapas.`;
    if (mode === "only") {
      const sel = [...onlyPhases].map(k => PHASE_NAME[k]);
      return sel.length ? `Executa somente: ${sel.join(" ? ")}.` : "Selecione as etapas que deseja executar.";
    }
    const sel = [...skipPhases].map(k => PHASE_NAME[k]);
    return sel.length ? `Executa tudo, exceto: ${sel.join(", ")}.` : "Selecione as etapas que deseja pular.";
  };

  return (
    <div>
      <div className="page-head">
        <h1 className="text-3xl">Criar V�deo</h1>
        <p>Descreva o tema. O nome do projeto � gerado automaticamente a partir do texto.</p>
      </div>

      <Section title="Roteiro e tema">
        <Field label="Sobre o que � o v�deo?">
          <textarea
            className="field-input field-textarea"
            rows={5}
            placeholder="Ex.: Frida e Luna descobrem que o aspirador de p� � um monstro"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <div className="flex justify-between items-center mt-3">
            <span className="text-[11px] mono" style={{ color: "var(--text-3)" }}>{prompt.length} caracteres</span>
            <span className="pill"><span className="dot" />projeto � <span className="mono">{slug}</span></span>
            {slugExists && (
              <span className="pill warn" style={{ marginLeft: 8 }}>
                <span className="dot" />projeto existente � Gerar vai retomar dos checkpoints
              </span>
            )}
          </div>
        </Field>
      </Section>

      <div className="card elevated">
        <div className="panel-body">
          <PipelineRail
            mode={mode} fromPhase={fromPhase} onlyPhases={onlyPhases} skipPhases={skipPhases}
            running={running} plan={plan} doneSet={doneSet}
            onFrom={setFromPhase} onToggle={togglePhase}
            liveRun={liveRun}
          />
        </div>
      </div>

      <Section title="Modo de execu��o">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {RUN_MODES.map((m) => (
            <label
              key={m.key}
              className={`radio-card ${mode === m.key ? "active" : ""}`}
              onClick={() => setMode(m.key)}
            >
              <input type="radio" name="runmode" checked={mode === m.key} readOnly />
              <div className="min-w-0">
                <div className="text-[13px] font-semibold" style={{ color: mode === m.key ? "var(--text)" : "var(--text-2)" }}>{m.label}</div>
                <div className="text-[10.5px] mt-0.5" style={{ color: "var(--text-3)" }}>{m.desc}</div>
              </div>
              {m.key === "from" && mode === m.key && (
                <select className="mini-select" style={{ maxWidth: 130, padding: "6px 10px", fontSize: 11 }} value={fromPhase} onChange={(e) => { setFromPhase(e.target.value); }}>
                  {PHASES.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
                </select>
              )}
            </label>
          ))}
        </div>

        {(mode === "only" || mode === "skip") && (
          <Field label={mode === "only" ? "Executar somente estas etapas" : "Pular estas etapas"} className="mt-5">
            <div className="flex flex-wrap gap-2">
              {PHASES.map((p) => {
                const on = mode === "only" ? onlyPhases.has(p.key) : skipPhases.has(p.key);
                return (
                  <button key={p.key} className={`chip ${on ? "on" : ""}`} onClick={() => togglePhase(p.key)}>
                    {p.label}
                  </button>
                );
              })}
            </div>
          </Field>
        )}

        <div className="statusline mt-5">
          <div className="label"><span style={{ color: "var(--indigo)" }}>plan</span>resumo</div>
          <div className="txt">{summary()}{force ? " � Checkpoints ser�o ignorados." : ""}</div>
        </div>
      </Section>

      {upload && (
        <Section title="Metadados do YouTube">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
            <Field label="ID do v�deo (atualizar metadados apenas)">
              <input className="field-input" value={ytVideoId} onChange={(e) => setYtVideoId(e.target.value)} placeholder="Vazio = upload novo v�deo" />
              <div className="text-[10px] mono mt-1" style={{ color: "var(--text-3)" }}>Se preenchido, atualiza apenas t�tulo/desc/tags/thumb do v�deo existente</div>
            </Field>
            <div className="flex flex-col">
              <label className="field-label" style={{ marginBottom: 8 }}>Thumbnail (opcional)</label>
              <div className="border rounded p-2 flex items-center gap-2 cursor-pointer" onClick={() => document.getElementById('yt-thumb-input').click()}>
                <span style={{ fontSize: 14 }}>key</span>
                <span>{ytThumbFile ? ytThumbFile.name : "Selecionar JPG/PNG"}</span>
              </div>
              <input id="yt-thumb-input" type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => { if (e.target.files[0]) setYtThumbFile(e.target.files[0]); }} />
            </div>
            <div className="flex flex-col">
              <label className="field-label" style={{ marginBottom: 8 }}>client_secret.json</label>
              <div className="border rounded p-2 flex items-center gap-2 cursor-pointer" onClick={() => document.getElementById('yt-secret-input').click()}>
                <span style={{ fontSize: 14 }}>key</span>
                <span>{ytSecretFile ? ytSecretFile.name : "Selecionar JSON"}</span>
              </div>
              <input id="yt-secret-input" type="file" accept=".json" style={{ display: "none" }} onChange={(e) => { if (e.target.files[0]) setYtSecretFile(e.target.files[0]); }} />
            </div>
          </div>
          <div className="space-y-3 mt-3">
            <Field label="T�tulo">
              <input className="field-input" value={ytTitle} onChange={(e) => setYtTitle(e.target.value)} placeholder="Vazio = usa o prompt do projeto" />
            </Field>
            <Field label="Descri��o">
              <textarea className="field-input field-textarea" rows={3} value={ytDesc} onChange={(e) => setYtDesc(e.target.value)} placeholder="Vazio = usa o prompt do projeto" />
            </Field>
            <Field label="Tags (v�rgula)">
              <input className="field-input" value={ytTags} onChange={(e) => setYtTags(e.target.value)} />
            </Field>
          </div>
        </Section>
      )}

      <Section title="Op��es">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
          <Switch checked={upload} onChange={() => setUpload(!upload)} label="Enviar ao YouTube" desc="Upload ap�s o render" />
          <Switch checked={force} onChange={() => setForce(!force)} label="Refazer tudo" desc="Ignora checkpoints" />
          <Switch checked={noParallel} onChange={() => setNoParallel(!noParallel)} label="Sem paralelismo" desc="Uma etapa por vez" />
          <Switch checked={skipCheck} onChange={() => setSkipCheck(!skipCheck)} label="Pular lint" desc="Re-render r�pido" />
        </div>
      </Section>

      <Section title="Voz e narra��o">
        <div className="suggest-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
          {[
            { label: "Voz", val: voice, set: setVoice, opts: VOICES },
            { label: "Velocidade", val: rate, set: setRate, opts: ["+5%", "+10%", "+12%", "+15%", "+20%"] },
            { label: "Tom", val: pitch, set: setPitch, opts: ["+5Hz", "+8Hz", "+10Hz", "+15Hz"] },
            { label: "Estilo", val: style, set: setStyle, opts: ["excited", "friendly", "calm", "energetic"] },
            { label: "Espera (s)", val: wait, set: setWait, opts: ["120", "180", "240", "300", "360"] },
          ].map((f) => (
            <div key={f.label}>
              <label className="field-label" style={{ marginBottom: 8 }}>{f.label}</label>
              <select value={f.val} onChange={(e) => f.set(e.target.value)} className="w-full">
                {f.opts.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Dura��o alvo">
        <div className="flex items-center justify-between mb-3">
          <span className="pill ok"><span className="dot" />{Math.floor(duration / 60)} min {duration % 60}s</span>
          <span className="text-[10.5px] mono" style={{ color: "var(--text-3)" }}>30s � 20min</span>
        </div>
        <input type="range" min="30" max="1200" step="10" value={duration}
          onChange={(e) => setDuration(parseInt(e.target.value))} />
        <div className="flex gap-2 mt-4">
          {DURATION_PRESETS.map(({ label, secs }) => (
            <button key={label} className={`chip ${duration === secs ? "on" : ""}`} onClick={() => setDuration(secs)}>{label}</button>
          ))}
        </div>
      </Section>

      <div className="flex flex-wrap items-center justify-end gap-3 pb-2">
        <Btn variant="primary" size="lg" icon={Sparkles} onClick={handleRun} loading={running}
          disabled={running}>
          Iniciar pipeline
        </Btn>
        {runId && (
          <Btn variant="danger" icon={X} onClick={async () => {
            try {
              await api.stopPipeline(runId);
              setDoneSet(new Set()); setPlan([]);
              toast("Execu��o parada.", "warn");
            } catch (e) { toast("Erro ao parar: " + e.message, "err"); }
          }}>
            Parar
          </Btn>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// PAGE: PUBLISH
// ============================================================================

const PagePublish = ({ toast, projects }) => {
  const [selected, setSelected] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [thumbFile, setThumbFile] = useState(null);
  const [secretFile, setSecretFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    yt_video_id: "", yt_title: "", yt_desc: "", yt_tags: "pixel art,anima��o,cachorro,divertido",
    yt_priv: "private", yt_mode: "manual", yt_cat: "24", yt_when: "",
    yt_kids: false,
  });

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleFile = (file, type) => {
    if (type === "video" && !file.name.toLowerCase().endsWith(".mp4")) {
      setFileError("Selecione um arquivo .mp4");
      toast("Formato inv�lido � a capa de v�deo precisa ser um MP4.", "warn");
      return;
    }
    setFileError(null);
    if (type === "video") setVideoFile(file);
    if (type === "thumb") setThumbFile(file);
    if (type === "secret") setSecretFile(file);
    toast(`Arquivo "${file.name}" vinculado.`, "ok");
  };

  const submit = async () => {
    if (!selected && !videoFile && !form.yt_video_id) {
      toast("Selecione um projeto, um arquivo MP4 ou informe o ID do v�deo existente.", "warn");
      return;
    }
    setSubmitting(true);
    try {
      await api.runPipeline({
        prompt: selected || "",
        mode: "only",
        phases: "compose,render",
        upload: true,
        ...form,
        yt_video: (videoFile && videoFile.path) || "",
        yt_thumb: (thumbFile && thumbFile.path) || "",
        yt_secret: (secretFile && secretFile.path) || "",
      });
      toast("Publica��o iniciada � acompanhe em Atividade.", "ok");
    } catch (e) {
      toast("Erro no upload: " + e.message, "err");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="page-head">
        <h1 className="text-3xl">Publicar no YouTube</h1>
        <p>Envie o MP4 final com metadados, visibilidade e agendamento completos.</p>
      </div>

      <Section title="Projetos dispon�veis">
        {projects.length === 0 ? (
          <div className="empty-state">
            <div className="big">Nenhum projeto</div>
            <div className="text-xs">Gere um v�deo na p�gina Criar primeiro.</div>
          </div>
        ) : (
          <div className="grid gap-2.5">
            {projects.map((p) => {
              const on = selected === p.slug;
              return (
                <button
                  key={p.slug}
                  onClick={() => setSelected(on ? null : p.slug)}
                  className="run-row text-left"
                  style={{
                    borderColor: on ? "rgba(139,92,246,.55)" : undefined,
                    background: on ? "rgba(139,92,246,.1)" : undefined,
                  }}
                >
                  <span className={`w-2 h-2 rounded-full flex-none ${p.video ? "" : "opacity-40"}`}
                    style={{ background: p.video ? "var(--green)" : "var(--text-3)" }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold truncate" style={{ color: "var(--text)" }}>
                      {p.prompt || p.slug}
                    </div>
                    <div className="text-[10.5px] mono mt-0.5" style={{ color: "var(--text-3)" }}>
                      {p.slug} � {p.done}/10 etapas
                    </div>
                  </div>
                  <span className={`pill ${p.video ? "ok" : ""}`}>
                    <span className="dot" />{p.video ? "v�deo pronto" : "sem render"}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </Section>

      <Section title="Ou escolher arquivo de v�deo (MP4)">
        <div className="suggest-grid">
          <FilePicker
            accept=".mp4"
            label="Selecione um arquivo MP4"
            sub="Clique e escolha o v�deo final do projeto"
            icon={Video}
            onFile={(f) => handleFile(f, "video")}
            fileName={videoFile ? videoFile.name : null}
            onRemove={() => setVideoFile(null)}
          />
        </div>
        {fileError && <p className="text-[11px] mt-2 mono" style={{ color: "var(--red)" }}>{fileError}</p>}
      </Section>

        <div className="yt-panel">
        <h2 className="mono" style={{ fontSize: 12, letterSpacing: ".14em", textTransform: "uppercase", color: "var(--amber)", marginBottom: 16 }}>Op��es de envio</h2>
        <div className="space-y-4 mb-6">
          <Field label="ID do v�deo existente (atualizar metadados apenas)">
            <input className="field-input" value={form.yt_video_id} onChange={set("yt_video_id")} placeholder="Vazio = enviar v�deo novo" />
            <div className="text-[10px] mono mt-1" style={{ color: "var(--text-3)" }}>Se preenchido, atualiza t�tulo/desc/tags/thumb do v�deo existente sem reenviar o MP4</div>
          </Field>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-5">
            <Field label="T�tulo do v�deo">
              <input className="field-input" value={form.yt_title} onChange={set("yt_title")} placeholder="Vazio = usa o prompt do projeto" />
            </Field>
            <Field label="Descri��o">
              <textarea className="field-input field-textarea" rows={3} value={form.yt_desc} onChange={set("yt_desc")} placeholder="Vazio = usa o prompt do projeto" />
            </Field>
            <Field label="Tags (v�rgula)">
              <input className="field-input" value={form.yt_tags} onChange={set("yt_tags")} />
            </Field>
          </div>
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Categoria">
                <select className="w-full" value={form.yt_cat} onChange={set("yt_cat")}>
                  <option value="24">Entretenimento</option>
                  <option value="1">Filmes e anima��o</option>
                  <option value="15">Animais de estima��o</option>
                  <option value="23">Com�dia</option>
                  <option value="22">Pessoas e blogs</option>
                </select>
              </Field>
              <Field label="Modo de envio">
                <select className="w-full" value={form.yt_mode} onChange={set("yt_mode")}>
                  {YT_MODES.map(m => <option key={m.key} value={m.key}>{m.label}</option>)}
                </select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Visibilidade">
                <select className="w-full" value={form.yt_priv} onChange={set("yt_priv")}>
                  {YT_PRIVACY.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
                </select>
              </Field>
              <Field label="Agendar publica��o">
                <input type="datetime-local" value={form.yt_when} onChange={set("yt_when")} />
              </Field>
            </div>
            <div>
              <label className="field-label" style={{ marginBottom: 8 }}>Feito para crian�as</label>
              <Switch checked={form.yt_kids} onChange={() => setForm({ ...form, yt_kids: !form.yt_kids })}
                label="Marcar como conte�do infantil" desc="Confira se a exig�ncia do YouTube se aplica ao canal" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 pt-6" style={{ borderTop: "1px solid var(--border-soft)" }}>
          <FilePicker
            accept="image/*"
            label="Thumbnail (opcional)"
            sub="JPG ou PNG"
            icon={ImageIcon}
            onFile={(f) => handleFile(f, "thumb")}
            fileName={thumbFile ? thumbFile.name : null}
            onRemove={() => setThumbFile(null)}
          />
          <FilePicker
            accept=".json"
            label="client_secret.json"
            sub="Credenciais OAuth do canal"
            icon={FileText}
            onFile={(f) => handleFile(f, "secret")}
            fileName={secretFile ? secretFile.name : null}
            onRemove={() => setSecretFile(null)}
          />
          <div className="flex flex-col justify-end items-stretch">
            <Btn variant="primary" size="lg" icon={Send} onClick={submit} loading={submitting}
              disabled={submitting || (!selected && !videoFile && !form.yt_video_id)}>
              Enviar ao YouTube
            </Btn>
            <p className="text-[10.5px] mt-2 text-center mono" style={{ color: "var(--text-3)" }}>
              No primeiro envio o navegador abre para autorizar o canal.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// PAGE: DAILY
// ============================================================================

const PageDaily = ({ toast, onDailyRun, onDailyStatus }) => {
  const { run, live } = useRunBus();
  const [schedules, setSchedules] = useState([]);
  const [topics, setTopics] = useState([]);
  const [statusTxt, setStatusTxt] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [newDate, setNewDate] = useState(iso(new Date()));
  const [newTime, setNewTime] = useState("09:00");
  const [newPrompt, setNewPrompt] = useState("");
  const [newSource, setNewSource] = useState("queue");
  const [newRecurrence, setNewRecurrence] = useState("none");
  const [loading, setLoading] = useState(false);
  const [viewMonth, setViewMonth] = useState(new Date());
  const [chosenTopic, setChosenTopic] = useState("");

  const fetchSchedules = useCallback(async () => {
    try {
      const data = await api.schedules();
      setSchedules(data.scheduled_videos || []);
    } catch (e) { toast("Erro ao carregar agendamentos: " + e.message, "err"); }
  }, []);

  const fetchTopics = useCallback(async () => {
    try {
      const data = await api.topics();
      setTopics(Array.isArray(data) ? data : []);
    } catch (e) { toast("Erro ao carregar t�picos: " + e.message, "err"); }
  }, []);

  let on = true;
  useEffect(() => {
    fetchSchedules();
    fetchTopics();
    onDailyStatus().then((t) => t && setStatusTxt(t));
    const t = setInterval(fetchSchedules, 30000);
    return () => { on = false; clearInterval(t); };
  }, []);

  const nextPending = useMemo(() => {
    const pend = schedules
      .filter((s) => !s.done && s.date && s.time)
      .sort((a, b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`));
    return pend[0] || null;
  }, [schedules]);

  const nextFireInfo = useMemo(() => {
    if (!nextPending) return null;
    const dt = new Date(`${nextPending.date}T${nextPending.time}:00`);
    const diff = Math.round((dt - new Date()) / 60000);
    if (isNaN(dt.getTime())) return null;
    const when = diff >= 0 ? `em ${diff < 60 ? diff + " min" : Math.floor(diff / 60) + "h" + String(diff % 60).padStart(2, "0")}` : `ATRASADO ${Math.abs(diff)} min`;
    return { dt, when, entry: nextPending };
  }, [nextPending]);

  const dailyEvents = (dateStr) => schedules.filter((s) => s.date === dateStr);
  const eventsToday = dailyEvents(iso(selectedDate));

  const handleAdd = async () => {
    if (!newDate || !newTime) {
      toast("Preencha data e hora do disparo.", "warn");
      return;
    }
    if (newSource === "topic" && !newPrompt.trim()) {
      toast("Escolha um t�pico espec�fico ou troque para fila autom�tica.", "warn");
      return;
    }
    setLoading(true);
    try {
      await api.createSchedule({
        date: newDate, time: newTime,
        prompt: newSource === "topic" ? newPrompt : "",
        source: newSource, recurrence: newRecurrence,
      });
      setNewPrompt(""); setNewTime("09:00"); setNewRecurrence("none");
      toast(`Agendamento criado para ${newDate} �s ${newTime}${newSource === "queue" ? " (fila autom�tica)" : ""}.`, "ok");
      await fetchSchedules();
    } catch (e) {
      toast("Erro ao agendar: " + e.message, "err");
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (id) => {
    try {
      await api.deleteSchedule(id);
      toast("Agendamento removido.", "warn");
      await fetchSchedules();
    } catch (e) {
      toast("Erro ao remover: " + e.message, "err");
    }
  };

  const daysInMonth = (year, month) => {
    const first = new Date(year, month, 1).getDay();
    const last = new Date(year, month + 1, 0).getDate();
    const prevLast = new Date(year, month, 0).getDate();
    const days = [];
    for (let i = 0; i < first; i++) days.push({ date: new Date(year, month, prevLast - first + i + 1), current: false });
    for (let i = 1; i <= last; i++) days.push({ date: new Date(year, month, i), current: true });
    const total = first + last;
    for (let i = 0; i < Math.ceil(total / 7) * 7 - total; i++) days.push({ date: new Date(year, month + 1, i + 1), current: false });
    return days;
  };

  const isToday = (d) => d.toDateString() === new Date().toDateString();
  const isSelected = (d) => d.toDateString() === selectedDate.toDateString();

  const monthNames = ["Janeiro", "Fevereiro", "Mar�o", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
  const dayNames = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];

  return (
    <div>
      <div className="page-head">
        <h1 className="text-3xl">Di�rio & Agendamento</h1>
        <p>Executor autom�tico, calend�rio editorial e fila de t�picos em um s� lugar.</p>
      </div>

      <Section title="Executor Di�rio" right={
        live ? (
          <span className="pill warn"><span className="dot live" />
            {run.slug === "daily" || run.source === "daily"
              ? `fila � ${phaseLabel(run.phase)}${run.detail ? ` � ${run.detail}` : ""}`
              : `outro run � ${phaseLabel(run.phase)}${run.detail ? ` � ${run.detail}` : ""}`}
          </span>
        ) : null
      }>
        <div className="flex flex-wrap items-center gap-2.5 mb-5">
          <Btn variant="primary" icon={Play} onClick={() => onDailyRun({})} size="md" title="Roda o executor di�rio completo agora">
            Executar agora
          </Btn>
          <Btn variant="ghost" size="sm" icon={Eye} onClick={() => onDailyRun({ dry_run: true })} title="Simula sem produzir nada">Simula��o</Btn>
          <Btn variant="ghost" size="sm" icon={Video} onClick={() => onDailyRun({ no_upload: true })} title="Produz mas n�o envia">N�o enviar</Btn>
          <Btn variant="ghost" size="sm" icon={Zap} onClick={() => onDailyRun({ force: true })} title="For�a a execu��o mesmo se j� rodou hoje">For�ar hoje</Btn>
          <div className="flex-1" />
          <Btn variant="ghost" size="sm" icon={List} onClick={async () => { const t = await onDailyStatus(); if (t) { setStatusTxt(t); toast("Status da fila atualizado.", "info"); } }}>
            Status da fila
          </Btn>
        </div>
        <Statusline label="status do executor" right={<span style={{ color: "var(--green)" }}>queue �</span>}>
          {statusTxt || "Consultando o executor di�rio�"}
        </Statusline>
        {nextFireInfo && (
          <div className="run-row mt-3" style={{ borderColor: nextFireInfo.when.startsWith("ATRASADO") ? "rgba(229,84,75,.5)" : "rgba(240,168,60,.35)" }}>
            <span className="pill ok" style={{ flex: "none" }}><span className="dot live" />scheduler</span>
            <span className="mono text-[12px] flex-none" style={{ color: "var(--amber)" }}>{nextFireInfo.entry.date} {nextFireInfo.entry.time}</span>
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] truncate" style={{ color: "var(--text)" }}>
                {nextFireInfo.entry.source === "queue" || !nextFireInfo.entry.prompt
                  ? "Fila autom�tica � pega o pr�ximo t�pico do dia"
                  : nextFireInfo.entry.prompt}
              </div>
              <div className="text-[9.5px] mono" style={{ color: "var(--text-3)" }}>
                {nextFireInfo.entry.source === "queue" || !nextFireInfo.entry.prompt ? "scheduler � fila" : nextFireInfo.entry.recurrence && nextFireInfo.entry.recurrence !== "none" ? nextFireInfo.entry.recurrence : "tema espec�fico"}
              </div>
            </div>
            <span className="pill warn" style={{ flex: "none" }}>
              <span className="dot" />dispara {nextFireInfo.when}
            </span>
          </div>
        )}
      </Section>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-5">
          <Section title={`Agendamentos � ${selectedDate.toLocaleDateString("pt-BR", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}`}>
            {eventsToday.length === 0 ? (
              <div className="empty-state" style={{ padding: 28 }}>
                <div className="big">Dia livre</div>
                <div className="text-xs">Nenhum v�deo agendado para esta data.</div>
              </div>
            ) : (
              <div className="space-y-2.5">
                {eventsToday.map((s) => (
                  <div key={s.id || s.time} className="run-row">
                    <span className={`w-2 h-2 rounded-full flex-none`} style={{ background: s.done ? "var(--green)" : "var(--indigo)" }} />
                    <span className="mono text-[12px] flex-none" style={{ color: "var(--amber)" }}>{s.time}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] truncate" style={{ color: "var(--text)" }}>
                        {s.source === "queue" || !s.prompt ? "Fila autom�tica � pega o pr�ximo t�pico do dia" : s.prompt}
                      </div>
                      <div className="text-[9.5px] mono" style={{ color: "var(--text-3)" }}>
                        {s.source === "queue" || !s.prompt ? "scheduler � fila" : s.recurrence && s.recurrence !== "none" ? s.recurrence : "tema espec�fico"}
                      </div>
                    </div>
                    <span className={`pill ${s.done ? "ok" : "warn"}`}><span className="dot" />{s.done ? "conclu�do" : "pendente"}</span>
                    <button onClick={() => handleRemove(s.id)} title="Remover" className="theme-toggle" style={{ width: 30, height: 30 }}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Agendar novo v�deo">
            <Field label="De onde vem o v�deo?">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className={`radio-card ${newSource === "queue" ? "active" : ""}`} onClick={() => setNewSource("queue")}>
                  <input type="radio" name="sched-source" checked={newSource === "queue"} readOnly />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold" style={{ color: newSource === "queue" ? "var(--text)" : "var(--text-2)" }}>
                      Fila autom�tica
                    </div>
                    <div className="text-[10.5px] mt-0.5" style={{ color: "var(--text-3)" }}>
                      Pega sozinho o pr�ximo t�pico da fila � datas comemorativas t�m prioridade e nada se repete.
                    </div>
                  </div>
                </label>
                <label className={`radio-card ${newSource === "topic" ? "active" : ""}`} onClick={() => setNewSource("topic")}>
                  <input type="radio" name="sched-source" checked={newSource === "topic"} readOnly />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold" style={{ color: newSource === "topic" ? "var(--text)" : "var(--text-2)" }}>
                      T�pico espec�fico
                    </div>
                    <div className="text-[10.5px] mt-0.5" style={{ color: "var(--text-3)" }}>
                      Voc� escolhe ou digita o tema abaixo.
                    </div>
                  </div>
                </label>
              </div>
            </Field>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <Field label="Data">
                <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
              </Field>
              <Field label="Hora">
                <input type="time" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
              </Field>
              <Field label="Recorr�ncia">
                <select className="w-full" value={newRecurrence} onChange={(e) => setNewRecurrence(e.target.value)}>
                  {RECURRENCE_OPTS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
                </select>
              </Field>
            </div>

            {newSource === "topic" ? (
              <Field label="Prompt / tema do v�deo" className="mt-2">
                <textarea rows={2} className="field-input field-textarea" value={newPrompt} onChange={(e) => setNewPrompt(e.target.value)}
                  placeholder="Ex.: Frida e Luna descobrem o aspirador" />
              </Field>
            ) : (
              <div className="statusline mt-3">
                <div className="label"><span style={{ color: "var(--green)" }}>auto �</span>fila inteligente</div>
                <div className="txt">
                  Sem tema definido: no hor�rio agendado o executor escolhe sozinho o pr�ximo assunto.
                  Prioridade para datas comemorativas do dia (linhas @MM-DD de topics.txt), depois a fila comum
                  em ordem � nenhum t�pico � repetido.
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Btn variant="primary" icon={Clock} onClick={handleAdd} loading={loading}>Agendar</Btn>
            </div>
          </Section>

          <Section title="T�picos dispon�veis" right={<span className="pill"><span className="dot" />{topics.length} fila</span>}>
            <div style={{ maxHeight: 320, overflow: "auto", paddingRight: 4 }}>
              {topics.length === 0 ? (
                <div className="empty-state" style={{ padding: 24 }}>
                  <div className="big">Fila vazia</div>
                  <div className="text-xs">Adicione t�picos em scripts/topics.txt</div>
                </div>
              ) : (
                <div className="grid gap-1.5">
                  {topics.map((t, i) => (
                    <button
                      key={i}
                      className={`topic-row ${chosenTopic === t ? "on" : ""}`}
                      onClick={() => { setNewPrompt(t); setChosenTopic(t); toast("T�pico carregado no rascunho.", "info"); }}
                    >
                      <span className="truncate">{t}</span>
                      {chosenTopic === t && <CheckCircle size={14} style={{ flex: "none" }} />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </Section>
        </div>

        <div className="lg:col-span-7 space-y-8">
          <Section title={`Agendamentos � ${selectedDate.toLocaleDateString("pt-BR", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}`}>
            {eventsToday.length === 0 ? (
              <div className="empty-state" style={{ padding: 28 }}>
                <div className="big">Dia livre</div>
                <div className="text-xs">Nenhum v�deo agendado para esta data.</div>
              </div>
            ) : (
              <div className="space-y-2.5">
                {eventsToday.map((s) => (
                  <div key={s.id || s.time} className="run-row">
                    <span className={`w-2 h-2 rounded-full flex-none`} style={{ background: s.done ? "var(--green)" : "var(--indigo)" }} />
                    <span className="mono text-[12px] flex-none" style={{ color: "var(--amber)" }}>{s.time}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] truncate" style={{ color: "var(--text)" }}>
                        {s.source === "queue" || !s.prompt ? "Fila autom�tica � pega o pr�ximo t�pico do dia" : s.prompt}
                      </div>
                      <div className="text-[9.5px] mono" style={{ color: "var(--text-3)" }}>
                        {s.source === "queue" || !s.prompt ? "scheduler � fila" : s.recurrence && s.recurrence !== "none" ? s.recurrence : "tema espec�fico"}
                      </div>
                    </div>
                    <span className={`pill ${s.done ? "ok" : "warn"}`}><span className="dot" />{s.done ? "conclu�do" : "pendente"}</span>
                    <button onClick={() => handleRemove(s.id)} title="Remover" className="theme-toggle" style={{ width: 30, height: 30 }}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Agendar novo v�deo">
            <Field label="De onde vem o v�deo?">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className={`radio-card ${newSource === "queue" ? "active" : ""}`} onClick={() => setNewSource("queue")}>
                  <input type="radio" name="sched-source" checked={newSource === "queue"} readOnly />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold" style={{ color: newSource === "queue" ? "var(--text)" : "var(--text-2)" }}>
                      Fila autom�tica
                    </div>
                    <div className="text-[10.5px] mt-0.5" style={{ color: "var(--text-3)" }}>
                      Pega sozinho o pr�ximo t�pico da fila � datas comemorativas t�m prioridade e nada se repete.
                    </div>
                  </div>
                </label>
                <label className={`radio-card ${newSource === "topic" ? "active" : ""}`} onClick={() => setNewSource("topic")}>
                  <input type="radio" name="sched-source" checked={newSource === "topic"} readOnly />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold" style={{ color: newSource === "topic" ? "var(--text)" : "var(--text-2)" }}>
                      T�pico espec�fico
                    </div>
                    <div className="text-[10.5px] mt-0.5" style={{ color: "var(--text-3)" }}>
                      Voc� escolhe ou digita o tema abaixo.
                    </div>
                  </div>
                </label>
              </div>
            </Field>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <Field label="Data">
                <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
              </Field>
              <Field label="Hora">
                <input type="time" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
              </Field>
              <Field label="Recorr�ncia">
                <select className="w-full" value={newRecurrence} onChange={(e) => setNewRecurrence(e.target.value)}>
                  {RECURRENCE_OPTS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
                </select>
              </Field>
            </div>

            {newSource === "topic" ? (
              <Field label="Prompt / tema do v�deo" className="mt-2">
                <textarea rows={2} className="field-input field-textarea" value={newPrompt} onChange={(e) => setNewPrompt(e.target.value)}
                  placeholder="Ex.: Frida e Luna descobrem o aspirador" />
              </Field>
            ) : (
              <div className="statusline mt-3">
                <div className="label"><span style={{ color: "var(--green)" }}>auto �</span>fila inteligente</div>
                <div className="txt">
                  Sem tema definido: no hor�rio agendado o executor escolhe sozinho o pr�ximo assunto.
                  Prioridade para datas comemorativas do dia (linhas @MM-DD de topics.txt), depois a fila comum
                  em ordem � nenhum t�pico � repetido.
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Btn variant="primary" icon={Clock} onClick={handleAdd} loading={loading}>Agendar</Btn>
            </div>
          </Section>

          <Section title="T�picos dispon�veis" right={<span className="pill"><span className="dot" />{topics.length} fila</span>}>
            <div style={{ maxHeight: 320, overflow: "auto", paddingRight: 4 }}>
              {topics.length === 0 ? (
                <div className="empty-state" style={{ padding: 24 }}>
                  <div className="big">Fila vazia</div>
                  <div className="text-xs">Adicione t�picos em scripts/topics.txt</div>
                </div>
              ) : (
                <div className="grid gap-1.5">
                  {topics.map((t, i) => (
                    <button
                      key={i}
                      className={`topic-row ${chosenTopic === t ? "on" : ""}`}
                      onClick={() => { setNewPrompt(t); setChosenTopic(t); toast("T�pico carregado no rascunho.", "info"); }}
                    >
                      <span className="truncate">{t}</span>
                      {chosenTopic === t && <CheckCircle size={14} style={{ flex: "none" }} />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </Section>

          <Section title="Calend�rio mensal" right={<span className="pill"><span className="dot" />{viewMonth.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</span>}>
            <div className="flex items-center gap-4 mb-3">
              <Btn variant="ghost" size="sm" icon={ChevronLeft} onClick={() => setViewMonth((m) => { m.setMonth(m.getMonth() - 1); return m; })} />
              <span className="font-semibold mono text-[13px]">{viewMonth.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</span>
              <Btn variant="ghost" size="sm" icon={ChevronRight} onClick={() => setViewMonth((m) => { m.setMonth(m.getMonth() + 1); return m; })} />
            </div>
            <div className="calendar-grid">
              {dayNames.map((d) => (
                <div key={d} className="cal-day-name">{d}</div>
              ))}
              {daysInMonth(viewMonth.getFullYear(), viewMonth.getMonth()).map((day) => (
                <div
                  key={day.date.getTime()}
                  className={`cal-day ${day.current ? "" : "opacity-50"} ${isToday(day.date) ? "today" : ""} ${isSelected(day.date) ? "selected" : ""}`}
                  onClick={() => setSelectedDate(day.date)}
                >
                  <span className="text-[11px]">{day.date.getDate()}</span>
                </div>
              ))}
            </div>
          </Section>
        </div>
        <div className="lg:col-span-7 space-y-8">
          <Section title={`Agendamentos � ${selectedDate.toLocaleDateString("pt-BR", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}`}>
            {eventsToday.length === 0 ? (
              <div className="empty-state" style={{ padding: 28 }}>
                <div className="big">Dia livre</div>
                <div className="text-xs">Nenhum v�deo agendado para esta data.</div>
              </div>
            ) : (
              <div className="space-y-2.5">
                {eventsToday.map((s) => (
                  <div key={s.id || s.time} className="run-row">
                    <span className={`w-2 h-2 rounded-full flex-none`} style={{ background: s.done ? "var(--green)" : "var(--indigo)" }} />
                    <span className="mono text-[12px] flex-none" style={{ color: "var(--amber)" }}>{s.time}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] truncate" style={{ color: "var(--text)" }}>
                        {s.source === "queue" || !s.prompt ? "Fila autom�tica � pega o pr�ximo t�pico do dia" : s.prompt}
                      </div>
                      <div className="text-[9.5px] mono" style={{ color: "var(--text-3)" }}>
                        {s.source === "queue" || !s.prompt ? "scheduler � fila" : s.recurrence && s.recurrence !== "none" ? s.recurrence : "tema espec�fico"}
                      </div>
                    </div>
                    <span className={`pill ${s.done ? "ok" : "warn"}`}><span className="dot" />{s.done ? "conclu�do" : "pendente"}</span>
                    <button onClick={() => handleRemove(s.id)} title="Remover" className="theme-toggle" style={{ width: 30, height: 30 }}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Agendar novo v�deo">
            <Field label="De onde vem o v�deo?">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className={`radio-card ${newSource === "queue" ? "active" : ""}`} onClick={() => setNewSource("queue")}>
                  <input type="radio" name="sched-source" checked={newSource === "queue"} readOnly />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold" style={{ color: newSource === "queue" ? "var(--text)" : "var(--text-2)" }}>
                      Fila autom�tica
                    </div>
                    <div className="text-[10.5px] mt-0.5" style={{ color: "var(--text-3)" }}>
                      Pega sozinho o pr�ximo t�pico da fila � datas comemorativas t�m prioridade e nada se repete.
                    </div>
                  </div>
                </label>
                <label className={`radio-card ${newSource === "topic" ? "active" : ""}`} onClick={() => setNewSource("topic")}>
                  <input type="radio" name="sched-source" checked={newSource === "topic"} readOnly />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold" style={{ color: newSource === "topic" ? "var(--text)" : "var(--text-2)" }}>
                      T�pico espec�fico
                    </div>
                    <div className="text-[10.5px] mt-0.5" style={{ color: "var(--text-3)" }}>
                      Voc� escolhe ou digita o tema abaixo.
                    </div>
                  </div>
                </label>
              </div>
            </Field>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <Field label="Data">
                <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
              </Field>
              <Field label="Hora">
                <input type="time" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
              </Field>
              <Field label="Recorr�ncia">
                <select className="w-full" value={newRecurrence} onChange={(e) => setNewRecurrence(e.target.value)}>
                  {RECURRENCE_OPTS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
                </select>
              </Field>
            </div>

            {newSource === "topic" ? (
              <Field label="Prompt / tema do v�deo" className="mt-2">
                <textarea rows={2} className="field-input field-textarea" value={newPrompt} onChange={(e) => setNewPrompt(e.target.value)}
                  placeholder="Ex.: Frida e Luna descobrem o aspirador" />
              </Field>
            ) : (
              <div className="statusline mt-3">
                <div className="label"><span style={{ color: "var(--green)" }}>auto �</span>fila inteligente</div>
                <div className="txt">
                  Sem tema definido: no hor�rio agendado o executor escolhe sozinho o pr�ximo assunto.
                  Prioridade para datas comemorativas do dia (linhas @MM-DD de topics.txt), depois a fila comum
                  em ordem � nenhum t�pico � repetido.
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Btn variant="primary" icon={Clock} onClick={handleAdd} loading={loading}>Agendar</Btn>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// PAGE: TESTS
// ============================================================================

const PageTests = ({ running, toast }) => {
  const { attach } = useRunBus();
  const [testPrompt, setTestPrompt] = useState("V�deo de teste do pipeline � todas as etapas");
  const [resumeSlug, setResumeSlug] = useState("");
  const [fromPhase, setFromPhase] = useState("script");
  const [testRunId, setTestRunId] = useState(null);
  const [resumeRunId, setResumeRunId] = useState(null);

  const pollStatus = useCallback(async (id, setter) => {
    if (!id) return;
    try {
      const st = await api.pipelineStatus(id);
      if (st.status !== "running" && st.status !== "starting") setter(null);
    } catch (_) {}
  }, []);

  useEffect(() => {
    if (!testRunId) return;
    const t = setInterval(() => pollStatus(testRunId, setTestRunId), 3000);
    return () => clearInterval(t);
  }, [testRunId, pollStatus]);

  useEffect(() => {
    if (!resumeRunId) return;
    const t = setInterval(() => pollStatus(resumeRunId, setResumeRunId), 3000);
    return () => clearInterval(t);
  }, [resumeRunId, pollStatus]);

  const handleTest = async () => {
    try {
      const res = await api.runPipeline({
        prompt: testPrompt, mode: "auto", force: true, skip_check: true,
        voice: "pt-BR-ThalitaNeural", rate: "+12%", pitch: "+8Hz",
        style: "excited", wait: "240", duration: 120,
        upload: false,
      });
      setTestRunId(res.run_id);
      attach(res.run_id, { slug: slugify(testPrompt), prompt: testPrompt, source: "test" });
      toast("Teste completo iniciado � run " + res.run_id, "ok");
    } catch (e) {
      toast("Erro no teste: " + e.message, "err");
    }
  };

  const handleResume = async () => {
    if (!resumeSlug.trim()) { toast("Informe o slug do projeto.", "warn"); return; }
    try {
      const res = await api.resumePipeline(resumeSlug.trim(), true, fromPhase);
      setResumeRunId(res.run_id);
      attach(res.run_id, { slug: resumeSlug.trim(), prompt: resumeSlug.trim(), source: "resume" });
      toast("Retomada iniciada � run " + res.run_id, "ok");
    } catch (e) {
      toast("Erro na retomada: " + e.message, "err");
    }
  };

  const handleStop = async (id) => {
    try {
      await api.stopPipeline(id);
      if (id === testRunId) setTestRunId(null);
      if (id === resumeRunId) setResumeRunId(null);
      toast("Execu��o parada.", "warn");
    } catch (e) {
      toast("Erro ao parar: " + e.message, "err");
    }
  };

  return (
    <div>
      <div className="page-head">
        <h1 className="text-3xl">Testes de Pipeline</h1>
        <p>Valida��o r�pida das 10 etapas e retomada cir�rgica de qualquer ponto.</p>
      </div>

      <Section title="Modo Teste (todas as etapas)">
        <Field label="Prompt de teste">
          <input className="field-input" value={testPrompt} onChange={(e) => setTestPrompt(e.target.value)} />
        </Field>
        <div className="flex gap-3 pt-3">
          <Btn variant="primary" icon={TestTube} onClick={handleTest} loading={running && !testRunId} disabled={(running && !testRunId) || testRunId}>
            Executar Teste Completo
          </Btn>
          {testRunId && (
            <Btn variant="danger" icon={X} onClick={() => handleStop(testRunId)}>Parar</Btn>
          )}
        </div>
        <div className="statusline mt-5">
          <div className="label"><span style={{ color: "var(--blue)" }}>info �</span>o que o modo teste faz</div>
          <div className="txt">
            For�a reexecu��o de todas as 10 fases (ignora checkpoints) � dura��o reduzida (2 min) para valida��o
            r�pida � pula o lint de render � nunca envia ao YouTube.
          </div>
        </div>
      </Section>

      <Section title="Retomada de qualquer ponto">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Field label="Slug do projeto" className="md:col-span-1">
            <input className="field-input" value={resumeSlug} onChange={(e) => setResumeSlug(e.target.value)} placeholder="video-engracado-sobre-buldogue" />
          </Field>
          <Field label="Retomar a partir de">
            <select className="w-full" value={fromPhase} onChange={(e) => setFromPhase(e.target.value)}>
              {PHASES.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
            </select>
          </Field>
        </div>
        <div className="flex gap-3 pt-3">
          <Btn variant="ghost" icon={ArrowRight} onClick={handleResume} loading={running && !resumeRunId}
            disabled={(running && !resumeRunId) || !resumeSlug.trim() || resumeRunId}>
            Retomar Execu��o
          </Btn>
          {resumeRunId && (
            <Btn variant="danger" icon={X} onClick={() => handleStop(resumeRunId)}>Parar</Btn>
          )}
        </div>
        <div className="statusline mt-5">
          <div className="label"><span style={{ color: "var(--blue)" }}>info �</span>como funciona</div>
          <div className="txt">
            L� o checkpoint salvo em project.json � reexecuta apenas as fases a partir do ponto escolhido �
            �til para corrigir uma etapa sem recome�ar o projeto do zero.
          </div>
        </div>
      </Section>
    </div>
  );
};

// ============================================================================
// PAGE: ACTIVITY
// ============================================================================

const PageActivity = ({ toast }) => {
  const { logs, connected, clear } = useLogsBus();
  const [projectSlug, setProjectSlug] = useState("");
  const [projectStatus, setProjectStatus] = useState(null);
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    let on = true;
    const load = () => api.pipelineRuns().then((r) => on && setRuns(Array.isArray(r) ? r : [])).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => { on = false; clearInterval(t); };
  }, []);

  const checkProjectStatus = async () => {
    if (!projectSlug.trim()) { toast("Informe o slug do projeto.", "warn"); return; }
    try {
      const st = await api.projectStatus(projectSlug.trim());
      setProjectStatus(st);
      toast(`Status carregado: ${st.slug || projectSlug}.`, "info");
    } catch (e) {
      setProjectStatus(null);
      toast("Projeto n�o encontrado: " + e.message, "err");
    }
  };

  const levelCls = (l) => l === "err" ? "err" : l === "ok" ? "ok" : l === "warn" ? "warn" : "run";

  return (
    <div>
      <div className="page-head flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Atividade & Observabilidade</h1>
          <p>Telemetria completa: logs ao vivo, execu��es e estado dos projetos.</p>
        </div>
      </div>

      <div className="telemetry-strip">
        <span className={`pill ${connected ? "ok" : "err"}`}><span className="dot live" />
          {connected ? "Conectado (WebSocket)" : "Desconectado"}
        </span>
        <span className="pill"><span className="dot" />{logs.length} eventos</span>
        <div className="flex-1" />
        <Btn variant="ghost" size="sm" icon={RotateCw} onClick={clear}>Limpar log</Btn>
      </div>

      <Section title="Status do projeto" right={
        <div className="flex gap-2">
          <input
            className="field-input"
            style={{ padding: "7px 12px", fontSize: 12, width: 260 }}
            value={projectSlug}
            onChange={(e) => setProjectSlug(e.target.value)}
            placeholder="Slug do projeto (ex: video-engracado-sobre-buldogue)"
            onKeyDown={(e) => e.key === "Enter" && checkProjectStatus()}
          />
          <Btn variant="ghost" size="sm" icon={Monitor} onClick={checkProjectStatus}>Consultar</Btn>
        </div>
      }>
        {!projectStatus ? (
          <p className="text-[11.5px] mono" style={{ color: "var(--text-3)" }}>
            Informe o slug e clique em Consultar para ver fases conclu�das, v�deo e prompt do projeto.
          </p>
        ) : (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="kv"><span className="k">slug</span><span className="v mono">{projectStatus.slug || "�"}</span></div>
              <div className="kv"><span className="k">v�deo</span>
                <span className={`v mono ${projectStatus.video_exists ? "" : ""}`}
                  style={{ color: projectStatus.video_exists ? "var(--green)" : "var(--text-3)" }}>
                  {projectStatus.video_exists ? "existe" : "n�o encontrado"}
                </span>
              </div>
              <div className="kv"><span className="k">prompt</span><span className="v">{projectStatus.prompt || "�"}</span></div>
              <div className="kv"><span className="k">fases prontas</span>
                <span className="v mono">{Object.values(projectStatus.phases || {}).filter((v) => v && v.done).length}/10</span>
              </div>
            </div>
            {projectStatus.phases && (
              <div className="flex flex-wrap gap-1.5 mt-4">
                {Object.entries(projectStatus.phases).map(([k, v]) => (
                  <span key={k} className={`chip ${v && v.done ? "on" : ""}`} style={{ cursor: "default" }}>
                    {k}{v && v.done ? " ?" : ""}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </Section>

      <Section title="Execu��es do pipeline">
        {runs.length === 0 ? (
          <p className="text-[11.5px] mono" style={{ color: "var(--text-3)" }}>
            Nenhuma execu��o ativa ou recente registrada pelo barramento.
          </p>
        ) : (
          <div className="grid gap-2">
            {runs.map((r, i) => (
              <div key={r.run_id || i} className="run-row">
                <span className="mono text-[11.5px]" style={{ color: "var(--amber)" }}>{(r.run_id || "").slice(0, 10)}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] truncate" style={{ color: "var(--text)" }}>{r.prompt || r.slug || "�"}</div>
                </div>
                <span className={`pill ${r.status === "running" || r.status === "starting" ? "warn" : r.status === "ok" || r.status === "done" ? "ok" : "err"}`}>
                  <span className={`dot ${r.status === "running" || r.status === "starting" ? "live" : ""}`} />{r.status || "desconhecido"}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="logs-panel" style={{ maxHeight: 460 }}>
        <div className="logs-header">
          <span className="logs-title">Logs ao vivo</span>
          <span className="mono text-[10px]" style={{ color: "var(--text-3)" }}>streaming via WebSocket � tempo real</span>
        </div>
        <div className="logs-body">
          {logs.length === 0 && (
            <p className="mono text-center p-14 text-[11px]" style={{ color: "var(--text-3)" }}>
              Nenhum log ainda. Dispare um pipeline para ver a telemetria aqui.
            </p>
          )}
          {logs.map((log, i) => (
            <div key={i} className="log-entry">
              <span className="log-time">{(log.ts || "").split("T")[1]?.split(".")[0] || "--:--:--"}</span>
              <span className={`log-level ${levelCls(log.level)}`}>{(log.level || "info").toUpperCase()}</span>
              <span className="log-msg">{log.msg}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// PAGE: EXECUTIVO
// ============================================================================

const PageExecutivo = ({ toast }) => {
  const { logs, connected } = useLogsBus();
  const { run: busRun, live: busLive } = useRunBus();
  const [telemetry, setTelemetry] = useState(null);
  const [runs, setRuns] = useState([]);
  const [agentStatus, setAgentStatus] = useState(null);
  const [nextFire, setNextFire] = useState(null);

  useEffect(() => {
    let on = true;
    const loadTelemetry = async () => {
      try {
        const t = await api.telemetry();
        on && setTelemetry(t);
      } catch (e) {
        console.warn("telemetry error", e);
      }
    };
    const loadRuns = async () => {
      try {
        const r = await api.pipelineRuns();
        on && setRuns(Array.isArray(r) ? r : []);
      } catch (e) {}
    };
    const loadAgent = async () => {
      try {
        const a = await api.dailyAgentStatus?.();
        on && setAgentStatus(a);
      } catch (e) {}
    };
    const loadNextFire = async () => {
      try {
        const s = await api.schedules();
        const now = new Date();
        let best = null, bestDiff = Infinity;
        for (const e of s.scheduled_videos || []) {
          if (e.done) continue;
          try {
            const dt = new Date(`${e.date}T${e.time}`);
            if (dt < now) continue;
            const diff = dt - now;
            if (diff < bestDiff) { bestDiff = diff; best = dt; }
          } catch {}
        }
        on && setNextFire(best);
      } catch (e) {}
    };
    loadTelemetry(); loadRuns(); loadAgent(); loadNextFire();
    const t = setInterval(() => { loadTelemetry(); loadRuns(); loadAgent(); loadNextFire(); }, 5000);
    return () => { on = false; clearInterval(t); };
  }, []);

  const fmtTime = (ts) => {
    if (!ts) return "�";
    try { return new Date(ts).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }); } catch { return "�"; }
  };

  const countdown = () => {
    if (!nextFire) return "�";
    const diff = nextFire - Date.now();
    if (diff <= 0) return "agora";
    const m = Math.floor(diff / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  const kpis = telemetry?.kpis || {};
  const projects = telemetry?.projects || [];
  const liveRuns = telemetry?.active_runs || [];

  const [, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const activeRun = (busLive && busRun)
    || liveRuns.find(r => r.status === "running" || r.status === "starting" || r.status === "uploading")
    || runs.find(r => r.status === "running" || r.status === "starting" || r.status === "uploading");
  const lastProject = projects.find(p => p.total_duration_s > 0)
    || projects.find(p => Object.values(p.phases || {}).some(v => v?.done));

  const live = !!activeRun;
  const phaseData = live ? { ...(activeRun?.phases || {}) } : {};
  if (live && activeRun?.current_phase) {
    phaseData[activeRun.current_phase] = {
      ...(phaseData[activeRun.current_phase] || {}),
      running: true,
      done: false,
    };
  }
  const histLabel = live
    ? (activeRun.slug || activeRun.run_id?.slice(0, 8) || "run ativo")
    : "nenhuma execu��o ao vivo";

  const sparkData = [...projects]
    .filter(p => p.total_duration_s > 0)
    .sort((a, b) => new Date(a.last_activity || 0) - new Date(b.last_activity || 0))
    .slice(-10)
    .map(p => p.total_duration_s / 60);
  const avgMin = sparkData.length ? Math.round(sparkData.reduce((a, b) => a + b, 0) / sparkData.length) : 0;

  const logHist = Array(30).fill(0);
  const now = Date.now();
  for (const log of logs) {
    try {
      const logTime = new Date(log.ts).getTime();
      const diffMin = Math.floor((now - logTime) / 60000);
      if (diffMin >= 0 && diffMin < 30) logHist[29 - diffMin]++;
    } catch {}
  }

  const handleStopAgent = async () => {
    try {
      await api.dailyStopAgent?.();
      toast("Comando de parada do agente externo enviado.", "warn");
      setTimeout(() => loadAgent(), 1000);
    } catch (e) { toast("Falha ao parar agente: " + e.message, "err"); }
  };

  const handleUnpauseRequeue = async () => {
    try {
      const r = await api.dailyUnpauseRequeue?.();
      toast(r?.ok ? "Assunto recolocado na fila." : "Falha: " + (r?.error || "desconhecido"), r?.ok ? "ok" : "err");
    } catch (e) { toast("Falha ao recolocar: " + e.message, "err"); }
  };

  return (
    <div className="exec-panel">
      <div className="page-head flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl">Painel Executivo</h1>
          <p>Vis�o gerencial: KPIs, fases, timeline, pr�ximos disparos e logs gr�ficos.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Btn variant="ghost" size="sm" icon={RotateCw} onClick={() => { api.telemetry().then(setTelemetry); api.pipelineRuns().then(r => setRuns(Array.isArray(r) ? r : [])); }}>Atualizar</Btn>
          <Btn variant="ghost" size="sm" icon={RotateCw} onClick={handleUnpauseRequeue} disabled={!agentStatus?.active}>
            Recolocar na fila
          </Btn>
          <Btn variant="danger" size="sm" icon={X} onClick={async () => {
            try {
              const r = await api.stopAllPipelines();
              toast(`Parada enviada: ${(r.stopped || []).length} run(s).`, "warn");
            } catch (e) { toast("Falha ao parar tudo: " + e.message, "err"); }
          }}>Parar tudo</Btn>
        </div>
      </div>

      {agentStatus?.active && (
        <div className="card elevated exec-banner" style={{ borderLeft: "4px solid var(--amber)" }}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <Activity className="w-5 h-5 flex-none" style={{ color: "var(--amber)" }} />
              <div className="min-w-0">
                <div className="text-sm truncate" style={{ color: "var(--text)" }}>Agente externo ativo (schtasks/loop)</div>
                <div className="mono text-[10px] truncate" style={{ color: "var(--text-3)" }}>PIDs {agentStatus.pids?.join(", ")}</div>
              </div>
            </div>
            <Btn variant="danger" size="sm" icon={X} onClick={handleStopAgent}>Parar agente</Btn>
          </div>
        </div>
      )}

      {activeRun && (
        <div className="card elevated exec-banner" style={{ borderLeft: "4px solid var(--blue)" }}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <Activity className="w-5 h-5 flex-none" style={{ color: "var(--blue)" }} />
              <div className="min-w-0">
                <div className="text-sm truncate" style={{ color: "var(--text)" }}>
                  Run {activeRun.run_id?.slice(0, 8)} � {activeRun.status}
                  {activeRun.current_phase
                    ? ` � ${phaseLabel(activeRun.current_phase)}${activeRun.detail ? ` (${activeRun.detail})` : ""}`
                    : ""}
                </div>
                <div className="mono text-[10px] truncate" style={{ color: "var(--text-3)" }}>
                  {activeRun.prompt?.slice(0, 90) || activeRun.slug || "�"}
                </div>
              </div>
            </div>
            <Btn variant="danger" size="sm" icon={X} onClick={async () => {
              try {
                await api.stopPipeline(activeRun.run_id);
                toast("Run interrompido.", "warn");
              } catch (e) { toast("Falha ao parar: " + e.message, "err"); }
            }}>Parar run</Btn>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <KpiTile label="Projetos" value={kpis.total_projects ?? 0} icon={FolderSearch} />
        <KpiTile label="Conclu�dos" value={kpis.completed ?? 0} icon={CheckCircle} sub={kpis.success_rate !== undefined ? `${kpis.success_rate}%` : ""} />
        <KpiTile label="Tempo m�dio" value={kpis.avg_duration_s ? fmtDuration(kpis.avg_duration_s) : "�"} icon={Clock} />
        <KpiTile label="Pr�ximo disparo" value={countdown()} icon={Clock} sub={nextFire ? `em ${Math.max(0, Math.round((nextFire - Date.now()) / 60000))} min` : "sem agendamento"} />
      </div>

      <div className="exec-grid">
        <Section
          className="exec-cell span-5"
          title={live ? "Fases do run ao vivo" : "Fases � nenhuma execu��o ao vivo"}
          subtitle={live ? histLabel : "disparue um pipeline para ver o progresso aqui"}
        >
          <div className="gauge-grid">
            {PHASES.map(ph => {
              const pdata = phaseData[ph.key];
              const isCurrent = !!activeRun && (
                activeRun.current_phase === ph.key || pdata?.running
              );
              const done = !isCurrent && !!pdata?.done;
              const duration = pdata?.duration_s;
              return (
                <PhaseGauge key={ph.key} label={ph.label} done={done} duration={duration} current={isCurrent} />
              );
            })}
          </div>
        </Section>

        <Section
          className="exec-cell span-7"
          title={live ? "Waterfall ao vivo" : "Waterfall � nenhuma execu��o ao vivo"}
          subtitle={live ? histLabel : "o hist�rico de projetos conclu�dos fica nos KPIs acima"}
        >
          <Waterfall
            phases={PHASES}
            phaseData={phaseData}
            activeKey={activeRun ? (activeRun.current_phase || null) : null}
          />
        </Section>

        <Section
          className="exec-cell span-7"
          title="Dura��o dos projetos"
          subtitle={`m�dia ${avgMin} min � ${sparkData.length} amostras`}
        >
          <Sparkline data={sparkData} avg={avgMin} />
        </Section>

        <Section
          className="exec-cell span-5"
          title="Logs por minuto"
          subtitle={`�ltimos 30 min � ${logs.length} eventos`}
        >
          <LogHistogram data={logHist} />
          </Section>
        </div>
      <details className="card elevated exec-logs">
        <summary className="panel-head">
          <span className="font-medium">Logs ao vivo ({logs.length})</span>
          <span className={`pill ${connected ? "ok" : "err"}`}>
            <span className={`dot ${connected ? "live" : ""}`} />
            {connected ? "Conectado" : "Desconectado"}
          </span>
        </summary>
        <div className="logs-panel">
          <div className="logs-body">
            {logs.length === 0 && (
              <p className="mono text-center p-8 text-[11px]" style={{ color: "var(--text-3)" }}>
                Nenhum log ainda. Dispare um pipeline para ver a telemetria aqui.
              </p>
            )}
            {logs.slice(0, 120).map((log, i) => (
              <div key={i} className="log-entry">
                <span className="log-time">{(log.ts || "").split("T")[1]?.split(".")[0] || "--:--:--"}</span>
                <span className={`log-level ${log.level === "error" ? "err" : "ok"}`}>{(log.level || "info").toUpperCase()}</span>
                <span className="log-msg">{log.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </details>
    </div>
  );
};


// ============================================================================
// PAGE: SETTINGS
// ============================================================================

const PageSettings = ({ themeMode, setThemeMode, zoom, setZoom, toast }) => {
  const [persist, setPersist] = useState(true);
  const [duration, setDuration] = useState(300);
  const [voice, setVoice] = useState("pt-BR-ThalitaNeural");
  const [rate, setRate] = useState("+12%");
  const [pitch, setPitch] = useState("+8Hz");
  const [noParallel, setNoParallel] = useState(false);
  const [skipCheck, setSkipCheck] = useState(false);
  const [publish, setPublish] = useState(false);
  const [privacy, setPrivacy] = useState("private");
  const [category, setCategory] = useState("24");
  const [tags, setTags] = useState("cachorro,anima��o,frida,luna");
  const [kids, setKids] = useState(false);
  const [mode, setMode] = useState("manual");

  // Load settings from API on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await api.getSettings();
        if (data.pipeline) {
          setDuration(data.pipeline.duration ?? 300);
          setVoice(data.pipeline.voice ?? "pt-BR-ThalitaNeural");
          setRate(data.pipeline.rate ?? "+12%");
          setPitch(data.pipeline.pitch ?? "+8Hz");
          setNoParallel(data.pipeline.no_parallel ?? false);
          setSkipCheck(data.pipeline.skip_check ?? false);
          setPublish(data.pipeline.publish ?? false);
        }
        if (data.youtube) {
          setPrivacy(data.youtube.privacy ?? "private");
          setCategory(data.youtube.category ?? "24");
          setTags(data.youtube.tags ?? "");
          setKids(data.youtube.kids ?? false);
          setMode(data.youtube.mode ?? "manual");
        }
      } catch (e) {
        // Silently ignore if backend not available
      }
    };
    loadSettings();
  }, []);

  // Save settings to API when they change
  useEffect(() => {
    const saveSettings = async () => {
      try {
        await api.putSettings({
          pipeline: { duration, voice, rate, pitch, no_parallel: noParallel, skip_check: skipCheck, publish },
          youtube: { privacy, category, tags, kids, mode },
        });
      } catch (e) {
        // Silently ignore if backend not available
      }
    };
    saveSettings();
  }, [duration, voice, rate, pitch, noParallel, skipCheck, publish, privacy, category, tags, kids, mode]);

  
  // Import VOICES and DURATION_PRESETS for settings
  const VOICES = [
    "pt-BR-ThalitaNeural", "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural",
    "en-US-AriaNeural", "en-US-GuyNeural",
  ];
  const DURATION_PRESETS = [
    { label: "3 min", secs: 180 },
    { label: "5 min", secs: 300 },
    { label: "10 min", secs: 590 },
    { label: "15 min", secs: 900 },
  ];
  
  const applyZoom = (z) => {
    setZoom(z);
    if (persist) toast(`Zoom definido para ${z * 100}% (salvo automaticamente).`, "info");
  };
  const applyTheme = (t) => {
    setThemeMode(t);
    if (persist) toast(`Tema definido para ${t === "auto" ? "autom�tico" : t === "dark" ? "escuro" : "claro"}.`, "info");
  };

  return (
    <div>
      <div className="page-head">
        <h1 className="text-3xl">Ajustes</h1>
        <p>Tema, zoom e prefer�ncias persistentes da interface.</p>
      </div>

      <div className="card elevated mb-8"><div className="panel-body">
        <h3 className="field-label" style={{ fontSize: 12 }}>Tema da interface</h3>
        <div className="flex gap-3 mt-3">
          {[
            { key: "auto", label: "Autom�tico" },
            { key: "light", label: "Claro" },
            { key: "dark", label: "Escuro" },
          ].map((t) => (
            <button key={t.key} className={`chip ${themeMode === t.key ? "on" : ""}`} style={{ padding: "10px 20px", fontSize: 12.5 }}
              onClick={() => applyTheme(t.key)}>
              {t.label}
            </button>
          ))}
        </div>
      </div></div>

      <div className="card elevated mb-8"><div className="panel-body">
        <h3 className="field-label" style={{ fontSize: 12 }}>Zoom da interface</h3>
        <div className="flex gap-3 mt-3">
          {ZOOM_LEVELS.map((z) => (
            <button key={z} className={`chip ${Math.round(zoom * 100) === z ? "on" : ""}`} style={{ padding: "10px 20px", fontSize: 12.5 }}
              onClick={() => applyZoom(z / 100)}>
              {z}%
            </button>
          ))}
        </div>
      </div></div>

      <div className="card elevated mb-8"><div className="panel-body space-y-4">
        <Switch checked={persist} onChange={() => { setPersist(!persist); toast(!persist ? "Ajustes ser�o salvos ao fechar." : "Ajustes n�o ser�o mais salvos.", "info"); }}
          label="Salvar ajustes ao fechar" desc="Lembra tema, zoom e prefer�ncias neste navegador" />
        <div style={{ borderTop: "1px solid var(--border-soft)", paddingTop: 18 }}>
          <h3 className="field-label" style={{ fontSize: 12 }}>Atalhos de teclado</h3>
          <div className="grid grid-cols-2 gap-3 mt-3">
            {[["Ctrl + Enter", "Gerar v�deo"], ["Ctrl + +", "Aumentar zoom"], ["Ctrl + -", "Diminuir zoom"], ["Ctrl + 0", "Resetar zoom"]].map(([k, v]) => (
              <div key={k} className="run-row" style={{ padding: "8px 12px" }}>
                <span className="mono text-[11px]" style={{ color: "var(--indigo)" }}>{k}</span>
                <div className="flex-1" />
                <span className="text-[11.5px]" style={{ color: "var(--text-2)" }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div></div>

      {/* Configura��es do pipeline */}
      <div className="card elevated mb-8"><div className="panel-body space-y-4">
        <h3 className="field-label" style={{ fontSize: 12 }}>Configura��es do pipeline</h3>
        <div className="flex gap-3 flex-wrap mt-3">
          <div className="flex items-center gap-2">
            <h4 className="field-label" style={{ fontSize: 12 }}>Dura��o</h4>
            <select value={duration} onChange={(e) => setDuration(parseInt(e.target.value))} className="input min-w-[100px]">
              {DURATION_PRESETS.map((p) => (
                <option key={p.secs} value={p.secs}>{p.label} ({p.secs} s)</option>
              ))}
              <option value="custom">Personalizado</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <h4 className="field-label" style={{ fontSize: 12 }}>Voz</h4>
            <select value={voice} onChange={(e) => setVoice(e.target.value)} className="input min-w-[200px]">
              {VOICES.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <h4 className="field-label" style={{ fontSize: 12 }}>Taxa de fala</h4>
            <input type="text" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="+12%" className="input min-w-[100px]" />
          </div>

          <div className="flex items-center gap-2">
            <h4 className="field-label" style={{ fontSize: 12 }}>Pitch</h4>
            <input type="text" value={pitch} onChange={(e) => setPitch(e.target.value)} placeholder="+8Hz" className="input min-w-[100px]" />
          </div>

          <div className="flex items-center gap-2 mt-8">
            <input type="checkbox" checked={noParallel} onChange={(e) => setNoParallel(e.target.checked)} className="checkbox" />
            <span className="text-xs">Sem paralelismo</span>
          </div>

          <div className="flex items-center gap-2 mt-8">
            <input type="checkbox" checked={skipCheck} onChange={(e) => setSkipCheck(e.target.checked)} className="checkbox" />
            <span className="text-xs">Pular check</span>
          </div>

          <div className="flex items-center gap-2 mt-8">
            <input type="checkbox" checked={publish} onChange={(e) => setPublish(e.target.checked)} className="checkbox" />
            <span className="text-xs">Publicar no YouTube</span>
          </div>
        </div>
      </div></div>

      {/* Configura��es do YouTube */}
      <div className="card elevated mb-8"><div className="panel-body space-y-4">
        <h3 className="field-label" style={{ fontSize: 12 }}>Configura��es do YouTube</h3>
        <div className="flex gap-3 flex-wrap mt-3">
          <div className="flex items-center gap-2">
            <h4 className="field-label" style={{ fontSize: 12 }}>Privacidade</h4>
            <select value={privacy} onChange={(e) => setPrivacy(e.target.value)} className="input min-w-[120px]">
              <option value="private">Privado</option>
              <option value="unlisted">N�o listado</option>
              <option value="public">P�blico</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <h4 className="field-label" style={{ fontSize: 12 }}>Categoria</h4>
            <select value={category} onChange={(e) => setCategory(e.target.value)} className="input min-w-[140px]">
              <option value="24">Com�dia</option>
              <option value="25">Educa��o</option>
              <option value="26">Entretenimento</option>
              <option value="27">M�sica</option>
              <option value="28">Not�cias</option>
              <option value="29">Pessoal</option>
              <option value="30">Ci�ncia</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <h4 className="field-label" style={{ fontSize: 12 }}>Tags</h4>
            <input type="text" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="cachorro,anima��o,frida,luna" className="input min-w-[200px]" />
          </div>

          <div className="flex items-center gap-2 mt-8">
            <input type="checkbox" checked={kids} onChange={(e) => setKids(e.target.checked)} className="checkbox" />
            <span className="text-xs">Feito para crian�as</span>
          </div>

          <div className="flex items-center gap-2 mt-8">
            <h4 className="field-label" style={{ fontSize: 12 }}>Modo</h4>
            <select value={mode} onChange={(e) => setMode(e.target.value)} className="input min-w-[120px]">
              <option value="manual">Manual</option>
              <option value="auto">Autom�tico</option>
              <option value="ask">Perguntar</option>
            </select>
          </div>
        </div>
      </div></div>

    </div>
  );
};

// ============================================================================
// ACTION BAR
// ============================================================================

const ActionBar = ({ running, runId, slug, phase, open, onRun, onResume, onStop, onUpload, onLogs }) => (
  <div className="actionbar">
    <div className="actionbar-inner" style={{ paddingLeft: open ? 284 : 96 }}>
      <div className="left-zone">
        <span className={`pill ${running ? "warn" : "ok"}`}>
          <span className={`dot ${running ? "live" : ""}`} />
          {running ? "Em execu��o" : "Pronto"}
        </span>
        <span className="mono text-[10.5px] hidden md:inline truncate" style={{ color: "var(--text-3)" }}>
          {running && phase
            ? `${slug && slug !== "�" ? slug + " � " : ""}${phaseLabel(phase)}${runId ? " � run " + runId.slice(0, 8) : ""}`
            : runId
              ? "run " + runId.slice(0, 8)
              : "barramento ocioso"}
        </span>
      </div>
      <div className="right-zone">
        <Btn variant="danger" size="sm" icon={X} onClick={onStop} disabled={!runId} title="Interrompe a execu��o atual">
          Parar
        </Btn>
        <Btn variant="ghost" size="sm" icon={RefreshCw} onClick={onResume} disabled={running || !slug || slug === "�"} title="Retoma o �ltimo projeto">
          Retomar
        </Btn>
        <Btn variant="primary" size="sm" icon={Play} onClick={onRun} disabled={running} title="Cria um v�deo a partir do tema">
          Gerar V�deo
        </Btn>
        <Btn variant="ghost" size="sm" icon={Upload} onClick={onUpload} title="Publicar no YouTube">
          Enviar YouTube
        </Btn>
        <Btn variant="ghost" size="sm" icon={Terminal} onClick={onLogs} title="Ver telemetria e logs">
          Logs
        </Btn>
      </div>
    </div>
  </div>
);

// ============================================================================
// SIDEBAR + SLATE
// ============================================================================

const Sidebar = ({ open, activePage, onNav, projects, onOpenProject }) => (
  <aside className={`sidebar ${open ? "open" : ""}`}>
    <div className="sidebar-head">
      <div className="brand-badge"><Film size={17} /></div>
      <div className="sidebar-open-block" style={{ overflow: "hidden" }}>
        <div className="brandmark-label">videomaker</div>
      </div>
    </div>
    <nav className="nav">
      {PAGES.map((pg) => {
        const Icon = pg.icon;
        const active = activePage === pg.key;
        return (
          <button key={pg.key} className={`nav-item ${active ? "active" : ""}`} onClick={() => onNav(pg.key)} title={pg.label}>
            <span className="icon"><Icon size={18} /></span>
            <span className="nav-label">{pg.label}</span>
          </button>
        );
      })}
    </nav>
    <div className="sidebar-footer">
      <div className="brand-mini">Projetos recentes</div>
      <div style={{ maxHeight: 190, overflow: "auto", paddingRight: 2 }} className="space-y-0.5">
        {projects.map((p) => (
          <button key={p.slug} className="recent-row" onClick={() => onOpenProject(p)} title={p.prompt || p.slug}>
            <span className={`rdot ${p.video ? "ok" : ""}`} />
            <span className="t">{p.prompt || p.slug}</span>
            <span className="n">{p.done}/10</span>
          </button>
        ))}
        {projects.length === 0 && (
          <div className="recent-row" style={{ cursor: "default" }}>
            <span className="t" style={{ color: "var(--text-3)" }}>Nenhum projeto</span>
          </div>
        )}
      </div>
      <div className="version" style={{ marginTop: 12 }}>v3.0.0 <span style={{ width: 6, height: 6, borderRadius: 99, background: "var(--green)", display: "inline-block" }} /></div>
    </div>
  </aside>
);

const Slate = ({ page, dark, onTheme, open, onToggleSb, apiOk, wsOk }) => (
  <header className="slate" style={{
    position: "sticky", top: 0, zIndex: 35,
    background: dark ? "rgba(10,10,12,.88)" : "rgba(239,228,201,.9)",
    backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
    borderBottom: "1px solid var(--border-soft)",
  }}>
    <span className="clapper" style={{ width: 34, height: 26 }} />
    <h1 style={{ fontSize: 14 }}>{PAGE_TITLES[page] || ""}</h1>
    <div className="spacer" />
    <span className={`pill ${apiOk ? "ok" : apiOk === false ? "err" : ""}`}>
      <span className={`dot ${apiOk ? "live" : ""}`} />API
    </span>
    <span className={`pill ${wsOk ? "ok" : "err"}`}>
      <span className={`dot ${wsOk ? "live" : ""}`} />WS
    </span>
    <button className="theme-toggle" onClick={onTheme} title={dark ? "Tema claro" : "Tema escuro"}>
      {dark ? <Sun size={15} /> : <Moon size={15} />}
    </button>
    <button className="theme-toggle" onClick={onToggleSb} title={open ? "Fechar menu" : "Abrir menu"}>
      <Menu size={15} />
    </button>
  </header>
);

// ============================================================================
// APP
// ============================================================================

const LiveStrip = ({ onOpenLogs }) => {
  const { run, live } = useRunBus();
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => setTick((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, [live]);
  if (!live || !run) return null;
  const elapsed = run.startedAt ? Math.max(0, Math.round((Date.now() - run.startedAt) / 1000)) : 0;
  const m = Math.floor(elapsed / 60);
  const s = String(elapsed % 60).padStart(2, "0");
  const title = run.prompt?.slice(0, 70) || run.slug || run.id;
  return (
    <button className="live-strip" onClick={onOpenLogs} title="Ver logs ao vivo">
      <span className="pill warn">
        <span className="dot live" />
        produzindo
      </span>
      <span className="mono text-[11px] truncate" style={{ color: "var(--text)" }}>{title}</span>
      <span className="pill">
        {run.detail || phaseLabel(run.phase)}
      </span>
      <span className="mono text-[10px]" style={{ color: "var(--text-3)" }}>{m}:{s}</span>
      <span className="mono text-[10px] hidden md:inline" style={{ color: "var(--text-3)" }}>
        run {run.id?.slice(0, 8)}
      </span>
      <span className="text-[10px]" style={{ color: "var(--accent)", marginLeft: "auto" }}>ver logs ?</span>
    </button>
  );
};

export default function App() {
  return (
    <RunBusProvider>
      <AppShell />
    </RunBusProvider>
  );
}

function AppShell() {
  const [page, setPage] = useState("create");
  const [themeMode, setThemeMode] = useState("dark");
  const [dark, setDark] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 1024);
  const [projects, setProjects] = useState([]);
  const [slug, setSlug] = useState("");
  const [toasts, setToasts] = useState([]);
  const [runRequest, setRunRequest] = useState(null);
  const [apiOk, setApiOk] = useState(null);
  const { run, live, attach, stopActive, connected } = useRunBus();
  const running = live;
  const runId = live ? (run?.id || null) : null;
  const currentPhase = live ? (run?.phase || null) : null;

  const pushToast = useCallback((msg, type = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-3), { id, msg, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  const refreshProjects = useCallback(() => {
    api.projects().then((r) => setProjects(Array.isArray(r) ? r : [])).catch(() => {});
  }, []);
  useEffect(refreshProjects, [refreshProjects]);

  useEffect(() => {
    if (themeMode === "auto") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      setDark(mq.matches);
      const f = (e) => setDark(e.matches);
      mq.addEventListener ? mq.addEventListener("change", f) : mq.addListener(f);
      return () => mq.removeEventListener ? mq.removeEventListener("change", f) : mq.removeListener(f);
    }
    setDark(themeMode === "dark");
  }, [themeMode]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
  }, [dark]);

  useEffect(() => {
    document.body.style.setProperty("--fs-scale", zoom);
  }, [zoom]);

  useEffect(() => {
    try {
      const s = JSON.parse(localStorage.getItem("vm-ui") || "{}");
      if (s.themeMode) setThemeMode(s.themeMode);
      if (s.zoom) setZoom(s.zoom);
    } catch (_) {}
  }, []);

  useEffect(() => {
    try { localStorage.setItem("vm-ui", JSON.stringify({ themeMode, zoom })); } catch (_) {}
  }, [themeMode, zoom]);

  useEffect(() => {
    let on = true;
    const tick = () => api.health()
      .then(() => on && setApiOk(true))
      .catch(() => on && setApiOk(false));
    tick();
    const t = setInterval(tick, 8000);
    return () => { on = false; clearInterval(t); };
  }, []);

  useEffect(() => {
    const h = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const k = e.key.toLowerCase();
      if (k === "enter") { e.preventDefault(); setPage("create"); setRunRequest({ type: "run", n: Date.now() }); }
      else if (e.key === "=") { e.preventDefault(); setZoom(z => Math.min(1.5, +(z + 0.25).toFixed(2))); }
      else if (e.key === "-") { e.preventDefault(); setZoom(z => Math.max(0.75, +(z - 0.25).toFixed(2))); }
      else if (k === "0") { e.preventDefault(); setZoom(1); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const handleRunComplete = (rid) => {
    if (rid) refreshProjects();
  };

  const handleResume = async () => {
    let s = (slug || "").trim();
    if (!s || s === "�") {
      s = projects[0] ? projects[0].slug : "";
      if (!s) { pushToast("Nenhum projeto dispon�vel para retomar.", "warn"); return; }
      setSlug(s);
    }
    try {
      const res = await api.resumePipeline(s, true);
      attach(res.run_id, { slug: s, prompt: s, source: "resume" });
      pushToast("Retomada iniciada � run " + res.run_id, "ok");
    } catch (e) {
      pushToast("Erro na retomada: " + e.message, "err");
    }
  };

  const handleStop = async () => {
    if (!runId) { pushToast("Nada em execu��o para parar.", "warn"); return; }
    const ok = await stopActive();
    pushToast(ok ? "Execu��o interrompida." : "Erro ao parar: falha no comando.", ok ? "warn" : "err");
  };

  const handleDailyRun = async (opts = {}) => {
    try {
      const res = await api.dailyRun(opts);
      attach(res.run_id, { slug: "daily", prompt: opts.dry_run ? "simula��o da fila" : "fila autom�tica", source: "daily" });
      pushToast((opts.dry_run ? "Simula��o di�ria" : "Executor di�rio") + " iniciado � run " + res.run_id, "ok");
      return true;
    } catch (e) {
      pushToast("Erro no executor di�rio: " + e.message, "err");
      return false;
    }
  };

  const handleDailyStatus = async () => {
    try {
      const st = await api.dailyStatus();
      if (typeof st === "string") return st;
      return st.output || st.msg || JSON.stringify(st, null, 2);
    } catch (e) {
      pushToast("Erro ao obter status do di�rio: " + e.message, "err");
      return null;
    }
  };

  const handleOpenProject = (p) => {
    setPage("create");
    setSlug(p.slug);
    pushToast(`Projeto ${p.slug} carregado em Criar/Retomar.`, "info");
  };

  useEffect(() => {
    if (run?.status === "ok") refreshProjects();
  }, [run?.status, run?.id, refreshProjects]);

  return (
    <div className="app">
      <Sidebar
        open={sidebarOpen}
        activePage={page}
        onNav={setPage}
        projects={projects}
        onOpenProject={handleOpenProject}
      />
      <main className="main">
        <Slate
          page={page}
          dark={dark}
          onTheme={() => setDark(!dark)}
          open={sidebarOpen}
          onToggleSb={() => setSidebarOpen(!sidebarOpen)}
          apiOk={apiOk}
          wsOk={connected}
        />
        <LiveStrip onOpenLogs={() => { setPage("activity"); }} />
        <AnimatePresence mode="wait">
          <motion.div
            key={page}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.22 }}
          >
            {page === "create" && (
              <PageCreate
                runRequest={runRequest}
                onRun={handleRunComplete}
                onFatal={(m) => pushToast(m, "err")}
                running={running}
                runId={runId}
                slug={slug}
                setSlug={setSlug}
                toast={pushToast}
              />
            )}
            {page === "publish" && <PagePublish toast={pushToast} projects={projects} />}
            {page === "daily" && (
              <PageDaily toast={pushToast} onDailyRun={handleDailyRun} onDailyStatus={handleDailyStatus} />
            )}
            {page === "tests" && (
              <PageTests running={running} toast={pushToast} />
            )}
            {page === "activity" && <PageActivity toast={pushToast} />}
            {page === "executivo" && <PageExecutivo toast={pushToast} />}
            {page === "settings" && (
              <PageSettings themeMode={themeMode} setThemeMode={setThemeMode} zoom={zoom} setZoom={setZoom} toast={pushToast} />
            )}
          </motion.div>
        </AnimatePresence>
      </main>
      <ActionBar
        running={running}
        runId={runId}
        slug={slug}
        phase={currentPhase}
        open={sidebarOpen}
        onRun={() => { setPage("create"); setRunRequest({ type: "run", n: Date.now() }); }}
        onResume={handleResume}
        onStop={handleStop}
        onUpload={() => { setPage("publish"); pushToast("P�gina de publica��o aberta.", "info"); }}
        onLogs={() => { setPage("activity"); pushToast("Telemetria aberta.", "info"); }}
      />
        <div className="fixed z-[100]" style={{ top: 76, right: 24, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`} style={{ position: "absolute", marginBottom: 0 }} onClick={() => setToasts((ts) => ts.filter((x) => x.id !== t.id))}>
            {t.msg}
          </div>
        ))}
      </div>
    </div>
  );
}

