import { fmtDuration } from "../utils/fmt";

const PhaseGauge = ({ label, done, duration, current }) => {
  const pct = done ? 100 : current ? 50 : 0;
  const circ = 2 * Math.PI * 16;
  return (
    <div className={`phase-gauge ${current ? "current" : done ? "done" : ""}`}>
      <div className="gauge-wrap">
        <svg viewBox="0 0 40 40" className="gauge-svg" aria-hidden="true">
          <circle className="gauge-bg" cx="20" cy="20" r="16" />
          <circle
            className="gauge-progress"
            cx="20" cy="20" r="16"
            strokeDasharray={`${(pct / 100) * circ} ${circ}`}
          />
          {current && <circle className="gauge-sweep" cx="20" cy="20" r="16" />}
        </svg>
        <span className="gauge-mark">{done ? "\u2713" : current ? "\u25CF" : ""}</span>
      </div>
      <div className="pg-text">
        <div className="pg-label" title={label}>{label}</div>
        <div className="pg-sub">
          {done ? "concluído" : current ? "em andamento" : "pendente"}
          {duration ? <span className="mono">- {fmtDuration(duration)}</span> : null}
        </div>
      </div>
    </div>
  );
};

const Waterfall = ({ phases, phaseData, activeKey }) => {
  const durs = phases.map(p => Number(phaseData[p.key]?.duration_s) || 0);
  const maxDur = Math.max(...durs, 1);
  const doneCount = phases.filter(p => phaseData[p.key]?.done).length;
  const totalDone = durs.reduce((a, b) => a + b, 0);
  return (
    <div className="waterfall">
      {phases.map((ph) => {
        const pd = phaseData[ph.key];
        const isDone = !!pd?.done;
        const isActive = !isDone && (activeKey === ph.key || (!activeKey && false));
        const dur = Number(pd?.duration_s) || 0;
        const w = isDone || isActive
          ? Math.max(10, Math.min(100, (dur / maxDur) * 100))
          : 4;
        return (
          <div key={ph.key} className="wf-row">
            <span className="wf-label" title={ph.label}>{ph.label}</span>
            <div className="wf-track">
              <div
                className={`wf-bar ${isDone ? "done" : isActive ? "active" : "pending"}`}
                style={{ width: `${w}%` }}
              >
                <span className="wf-time">{dur ? fmtDuration(dur) : "-"} </span>
              </div>
            </div>
          </div>
        );
      })}
      <div className="waterfall-legend">
        <span><span className="dot done" /> Concluído ({doneCount})</span>
        <span><span className="dot active" /> Em andamento</span>
        <span><span className="dot pending" /> Pendente</span>
        {totalDone > 0 && <span className="mono wf-total">Σ {fmtDuration(totalDone)}</span>}
      </div>
    </div>
  );
};

const Sparkline = ({ data, avg }) => {
  if (!data.length) {
    return (
      <div className="spark-empty">Sem projetos concluídos ainda</div>
    );
  }
  const w = 320, h = 110, pad = 14;
  const maxV = Math.max(...data, avg || 0) * 1.15 || 1;
  const px = (i) => pad + (i * (w - 2 * pad)) / Math.max(1, data.length - 1);
  const py = (v) => h - pad - (v / maxV) * (h - 2 * pad);
  const pts = data.map((v, i) => `${px(i)},${py(v)}`).join(" ");
  const area = `${pad},${h - pad} ${pts} ${px(data.length - 1)},${h - pad}`;
  return (
    <div className="spark-wrap">
      <svg viewBox={`0 0 ${w} ${h}`} className="sparkline-svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((t) => (
          <line key={t} x1={pad} y1={pad + t * (h - 2 * pad)} x2={w - pad} y2={pad + t * (h - 2 * pad)}
            stroke="var(--border)" strokeWidth={1} strokeDasharray="3,5" opacity="0.45" />
        ))}
        <polyline points={area} fill="url(#sparkFill)" />
        <polyline points={pts} fill="none" stroke="var(--accent)" strokeWidth={2.5}
          strokeLinecap="round" strokeLinejoin="round" />
        {data.map((v, i) => {
          const showLabel = i === 0 || i === data.length - 1 || v === Math.max(...data);
          return (
            <g key={i}>
              <circle cx={px(i)} cy={py(v)} r={4.5} fill="var(--accent)" stroke="var(--surface)" strokeWidth={2} />
              {showLabel && (
                <text x={px(i)} y={Math.max(12, py(v) - 9)} textAnchor="middle" className="spark-val">
                  {Math.round(v)}
                </text>
              )}
            </g>
          );
        })}
        {avg > 0 && (
          <line x1={pad} y1={py(avg)} x2={w - pad} y2={py(avg)}
            stroke="var(--amber)" strokeWidth={1.5} strokeDasharray="5,4" />
        )}
      </svg>
      <div className="spark-x">
        <span>mais antigo</span>
        <span>média {Math.round(avg) || 0} min</span>
        <span>mais recente</span>
      </div>
    </div>
  );
};

const LogHistogram = ({ data }) => {
  const maxV = Math.max(...data, 1);
  const total = data.reduce((a, b) => a + b, 0);
  return (
    <div className="hist-wrap">
      {total === 0 && (
        <span className="hist-empty">sem logs nos últimos 30 min</span>
      )}
      <div className="log-histogram">
        {data.map((v, i) => (
          <div
            key={i}
            className="log-bar"
            style={{
              height: `${Math.max(v ? 10 : 3, (v / maxV) * 100)}%`,
              opacity: v ? 0.9 : 0.14,
            }}
            title={`${v} logs há ${29 - i} min atrás`}
          />
        ))}
      </div>
      <div className="spark-x">
        <span>-30 min</span>
        <span>{total} eventos</span>
        <span>agora</span>
      </div>
    </div>
  );
};

export { PhaseGauge, Waterfall, Sparkline, LogHistogram };
