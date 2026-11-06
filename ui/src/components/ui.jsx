import { FileText, X } from "lucide-react";

const Section = ({ title, subtitle, children, right = null, className = "" }) => (
  <section className={className || "mb-8"}>
    <div className="flex items-center gap-3 pb-3 min-w-0">
      <div className="w-1 h-5 rounded-full flex-none" style={{ background: "linear-gradient(180deg,#8b5cf6,#4f46e5)" }} />
      <h2 className="section-title" style={{ padding: "0 0 2px", display: "inline" }}>{title}</h2>
      {subtitle && <span className="mono text-[10px] truncate" style={{ color: "var(--text-3)" }}>{subtitle}</span>}
      <div className="flex-1" />
      {right}
    </div>
    <div className="card elevated exec-card">
      <div className="panel-body">{children}</div>
    </div>
  </section>
);

const Btn = ({
  children, variant = "primary", onClick, className = "", icon: Icon,
  disabled = false, loading = false, size = "md", title,
}) => {
  const cls = [
    "btn",
    variant === "primary" && "btn-primary",
    variant === "ghost" && "btn-ghost",
    variant === "danger" && "btn-danger",
    size === "sm" && "btn-sm",
    loading && "btn-loading",
    className,
  ].filter(Boolean).join(" ");
  return (
    <button className={cls} onClick={onClick} disabled={disabled || loading} title={title}
      style={size === "lg" ? { padding: "12px 26px", fontSize: "14px", borderRadius: "12px" } : undefined}>
      {Icon && !loading && <Icon size={size === "sm" ? 13 : 15} />}
      <span>{children}</span>
    </button>
  );
};

const Switch = ({ checked, onChange, label, desc }) => (
  <label className="switch" onClick={onChange}>
    <input type="checkbox" checked={checked} readOnly />
    <span className="switch-track"><span className="switch-thumb" /></span>
    <span className="flex flex-col">
      <span className="switch-label">{label}</span>
      {desc && <span className="switch-desc">{desc}</span>}
    </span>
  </label>
);

const Field = ({ label, children, className = "" }) => (
  <div className={`field-group ${className}`}>
    <label className="field-label">{label}</label>
    {children}
  </div>
);

const FilePicker = ({ accept, label, sub, onFile, fileName, onRemove, icon: Icon = FileText }) => (
  <div>
    <div className="filebox">
      <input
        type="file"
        accept={accept}
        onChange={(e) => {
          const f = e.target.files && e.target.files[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
      <span className="icon"><Icon size={17} /></span>
      <span className="min-w-0 flex-1 block">
        <span className="file-title block">{fileName || label}</span>
        <span className="file-sub block">{fileName ? "Clique para trocar o arquivo" : sub || "Clique para escolher"}</span>
      </span>
    </div>
    {fileName && (
      <div className="flex justify-end mt-2">
        <button
          onClick={onRemove}
          className="inline-flex items-center gap-1.5 text-[10.5px] px-2 p-1 rounded-md transition-colors"
          style={{ border: "1px solid var(--border)", color: "var(--text-2)" }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "var(--red)"; e.currentTarget.style.borderColor = "var(--red)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-2)"; e.currentTarget.style.borderColor = "var(--border)"; }}
        >
          <X size={11} /> remover {fileName}
        </button>
      </div>
    )}
  </div>
);

const Statusline = ({ label, children, right = null }) => (
  <div className="statusline">
    <div className="label">{right}{label}</div>
    <div className="txt">{children}</div>
  </div>
);

export { Section, Btn, Switch, Field, FilePicker, Statusline };
