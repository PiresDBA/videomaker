import { createContext, useContext, useEffect, useMemo, useRef, useState, useCallback } from "react";
import { api } from "../services/api";

const WS_URL = "ws://127.0.0.1:8765/api/logs";
const REST_URL = "http://127.0.0.1:8765/api/logs/recent?limit=200";
const MAX_LOGS = 500;

export const PHASE_KEYS = [
  "script", "scenes", "images", "music", "narration",
  "timeline", "mix", "compose", "preprocess", "render",
];

export const isLive = (run) =>
  !!run && ["running", "starting", "uploading"].includes(run.status);

const RunCtx = createContext(null);
const LogsCtx = createContext(null);

export function RunBusProvider({ children }) {
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const [run, setRun] = useState(null);
  const runRef = useRef(null);
  const hydrated = useRef(false);

  useEffect(() => {
    runRef.current = run;
  }, [run]);

  const attach = useCallback((id, extra = {}) => {
    if (!id) return;
    setRun(() => ({
      slug: "",
      prompt: "",
      source: "manual",
      status: "starting",
      phase: null,
      phases: {},
      plan: null,
      startedAt: Date.now(),
      ...extra,
      id,
    }));
  }, []);

  const detach = useCallback(() => setRun(null), []);

  const stopActive = useCallback(async () => {
    const id = runRef.current?.id;
    if (!id) return false;
    try {
      await api.stopPipeline(id);
      setRun((prev) => (prev && prev.id === id ? { ...prev, status: "stopped" } : prev));
      return true;
    } catch (_) {
      return false;
    }
  }, []);

  const patchFromLog = useCallback((msg) => {
    if (!msg) return;
    const img = msg.match(/IMAGEM\s+(\d+)\s*\/\s*(\d+)/);
    if (img) {
      setRun((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          phase: "images",
          detail: `imagem ${img[1]}/${img[2]}`,
          phases: { ...prev.phases, images: { done: false, running: true } },
        };
      });
      return;
    }
    if (/QUARENTENA/.test(msg)) {
      setRun((prev) => (prev ? { ...prev, phase: "images", detail: "quarentena de imagens" } : prev));
      return;
    }
    const fase = msg.match(/FASE\s+([a-z]+)/i);
    if (fase) {
      const ph = fase[1].toLowerCase();
      if (PHASE_KEYS.includes(ph)) {
        setRun((prev) => {
          if (!prev) return prev;
          const phases = { ...prev.phases };
          if (prev.phase && prev.phase !== ph) phases[prev.phase] = { done: true, running: false };
          phases[ph] = { done: false, running: true };
          return {
            ...prev,
            phase: ph,
            detail: null,
            phases,
            status: prev.status === "starting" ? "running" : prev.status,
          };
        });
      }
      return;
    }
    const chk = msg.match(/CHECKPOINT\s+([a-z]+)/i);
    if (chk) {
      const ph = chk[1].toLowerCase();
      if (PHASE_KEYS.includes(ph)) {
        setRun((prev) => {
          if (!prev) return prev;
          return { ...prev, phases: { ...prev.phases, [ph]: { done: true, running: false } } };
        });
      }
      return;
    }
    if (/Planejado:\s*\[/.test(msg)) {
      try {
        const raw = msg.split("Planejado:")[1].trim().replace(/'/g, '"');
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) {
          setRun((prev) => (prev ? { ...prev, plan: arr } : prev));
        }
      } catch (_) {}
      return;
    }
    if (/conclu[ií]do com sucesso|PIPELINE CONCLUIDO/i.test(msg)) {
      setRun((prev) => (prev ? { ...prev, status: "ok" } : prev));
    } else if (/falhou com c[oó]digo|Traceback|ERRO:/i.test(msg)) {
      setRun((prev) => (prev && isLive(prev) ? { ...prev, status: "error" } : prev));
    } else if (/interrompido/i.test(msg)) {
      setRun((prev) => (prev ? { ...prev, status: "stopped" } : prev));
    }
  }, []);

  // WS único para toda a aplicação
  useEffect(() => {
    let ws = null;
    let closed = false;
    let timer = null;
    let attempts = 0;

    const hydrate = async () => {
      if (hydrated.current) return;
      try {
        const res = await fetch(REST_URL);
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data.logs) && data.logs.length) {
          hydrated.current = true;
          setLogs((prev) => (prev.length ? prev : data.logs.slice(-MAX_LOGS)));
        }
      } catch (_) {}
    };

    const connect = () => {
      if (closed) return;
      hydrate();
      try {
        ws = new WebSocket(WS_URL);
      } catch (_) {
        reconnect();
        return;
      }
      ws.onopen = () => {
        attempts = 0;
        setConnected(true);
      };
      ws.onclose = () => {
        setConnected(false);
        reconnect();
      };
      ws.onerror = () => {
        try { ws.close(); } catch (_) {}
      };
      ws.onmessage = (ev) => {
        try {
          const entry = JSON.parse(ev.data);
          setLogs((prev) => [entry, ...prev].slice(0, MAX_LOGS));
          patchFromLog(entry.msg || "");
        } catch (_) {}
      };
    };

    const reconnect = () => {
      if (closed) return;
      attempts += 1;
      const delay = Math.min(8000, 1200 * attempts);
      if (timer) clearTimeout(timer);
      timer = setTimeout(connect, delay);
    };

    connect();
    return () => {
      closed = true;
      if (timer) clearTimeout(timer);
      try { ws?.close(); } catch (_) {}
    };
  }, [patchFromLog]);

  // polling do run ativo (fonte de verdade)
  useEffect(() => {
    if (!run?.id) return;
    let on = true;
    const tick = async () => {
      try {
        const st = await api.pipelineStatus(run.id);
        if (!on) return;
        setRun((prev) => {
          if (!prev || prev.id !== run.id) return prev;
          return {
            ...prev,
            status: st.status || prev.status,
            slug: prev.slug || st.slug || "",
            prompt: prev.prompt || st.prompt || "",
            phase: st.current_phase || prev.phase,
            detail: st.detail || (st.current_phase === "images" ? prev.detail : null),
            phases: { ...prev.phases, ...(st.phases || {}) },
          };
        });
      } catch (_) {}
    };
    tick();
    const t = setInterval(tick, 2500);
    return () => { on = false; clearInterval(t); };
  }, [run?.id]);

  // adota run iniciado fora da UI (scheduler, CLI, daily)
  useEffect(() => {
    if (isLive(run)) return;
    let on = true;
    const adopt = async () => {
      try {
        const list = await api.pipelineRuns();
        const active = (Array.isArray(list) ? list : []).find(
          (r) => ["running", "starting", "uploading"].includes(r.status)
        );
        if (on && active && runRef.current?.id !== active.run_id) {
          setRun({
            id: active.run_id,
            slug: active.slug || "",
            prompt: active.prompt || "",
            source: "auto",
            status: active.status,
            phase: active.current_phase || null,
            phases: active.phases || {},
            plan: null,
            startedAt: Date.now(),
          });
        }
      } catch (_) {}
    };
    adopt();
    const t = setInterval(adopt, 6000);
    return () => { on = false; clearInterval(t); };
  }, [run?.id, run?.status]);

  const runCtx = useMemo(
    () => ({ run, live: isLive(run), attach, detach, stopActive, connected }),
    [run, connected, attach, detach, stopActive]
  );
  const logsCtx = useMemo(
    () => ({ logs, connected, clear: () => setLogs([]) }),
    [logs, connected]
  );

  return (
    <RunCtx.Provider value={runCtx}>
      <LogsCtx.Provider value={logsCtx}>{children}</LogsCtx.Provider>
    </RunCtx.Provider>
  );
}

export function useRunBus() {
  const ctx = useContext(RunCtx);
  if (!ctx) throw new Error("useRunBus fora de RunBusProvider");
  return ctx;
}

export function useLogsBus() {
  const ctx = useContext(LogsCtx);
  if (!ctx) throw new Error("useLogsBus fora de RunBusProvider");
  return ctx;
}

export function phaseLabel(phase) {
  const names = {
    script: "Roteiro",
    scenes: "Cenas",
    images: "Imagens",
    music: "Música",
    narration: "Narração",
    timeline: "Timeline",
    mix: "Mixagem",
    compose: "Composição",
    preprocess: "Pré-process.",
    render: "Render",
  };
  return names[phase] || phase || "iniciando";
}
