import { CheckCircle } from "lucide-react";
import { PHASES, PHASE_KEYS } from "../utils/phases";
import { isLive, phaseLabel } from "../hooks/useRunBus";

const PipelineRail = ({ mode, fromPhase, onlyPhases, skipPhases, running, plan, doneSet, onFrom, onToggle, liveRun }) => {
  const fromIdx = PHASE_KEYS.indexOf(fromPhase);
  const live = isLive(liveRun);
  const liveDone = new Set(
    Object.entries(liveRun?.phases || {})
      .filter(([, v]) => v && v.done)
      .map(([k]) => k)
  );
  const current = live ? liveRun.phase : null;
  const stateOf = (i, key) => {
    if (live) {
      if (key === current || liveRun.phases?.[key]?.running) return "current";
      if (liveDone.has(key) || liveRun.phases?.[key]?.done) return "done";
      if (Array.isArray(liveRun.plan) && !liveRun.plan.includes(key)) return "idle";
      return "prep";
    }
    if (running && plan) {
      if (doneSet.has(key)) return "done";
      if (plan.includes(key)) return "active";
      return "idle";
    }
    if (mode === "from") return i >= fromIdx ? "prep" : "idle";
    if (mode === "only") return onlyPhases.has(key) ? "prep" : "idle";
    if (mode === "skip") return skipPhases.has(key) ? "skip" : "prep";
    return "prep";
  };
  return (
    <div>
      <div className="flex items-baseline gap-3 mb-1 flex-wrap">
        <span className="section-title" style={{ padding: "0 0 2px", display: "inline" }}>Etapas do pipeline</span>
        <span className="mono text-[10px]" style={{ color: "var(--text-3)" }}>10 fases com checkpoints automáticos</span>
        {live && (
          <span className="pill warn">
            <span className="dot live" />
            ao vivo - {phaseLabel(current)}{liveRun.detail ? ` - ${liveRun.detail}` : ""}
          </span>
        )}
      </div>
      <div className="pipeline-rail" style={{ overflowX: "auto" }}>
        {PHASES.map((phase, i) => {
          const st = stateOf(i, phase.key);
          const Icon = phase.icon;
          return (
            <div
              key={phase.key}
              className={`pipeline-stage ${st}`}
              style={{ cursor: running ? "default" : (mode === "only" || mode === "skip" || mode === "from" ? "pointer" : "default") }}
              onClick={() => {
                if (running) return;
                if (mode === "from") onFrom(phase.key);
                else if (mode === "only" || mode === "skip") onToggle(phase.key);
              }}
            >
              <div className="line" />
              <div className="node">
                {st === "done" ? <CheckCircle size={13} /> : <Icon size={13} strokeWidth={2.1} />}
              </div>
              <div className="name">{phase.label}</div>
              <div className="sub">{phase.sub}</div>
            </div>
          );
        })}
      </div>
      {!running && mode === "from" && (
        <p className="text-[11px] mono mt-1" style={{ color: "var(--text-3)" }}>
          Clique em uma etapa para definir o ponto de partida.
        </p>
      )}
      {!running && (mode === "only" || mode === "skip") && (
        <p className="text-[11px] mono mt-1" style={{ color: "var(--text-3)" }}>
          Clique nas etapas para {mode === "only" ? "incluir" : "excluir"} do plano.
        </p>
      )}
    </div>
  );
};

export { PipelineRail };
