import React from "react";

export function KpiTile(props) {
  const Icon = props.icon;
  return (
    <div className="card elevated kpi-tile">
      <div className="panel-body">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="kpi-label">{props.label}</div>
            <div className="kpi-value" title={String(props.value)}>{props.value}</div>
            {props.sub && <div className="kpi-sub">{props.sub}</div>}
          </div>
          <Icon className="kpi-icon" />
        </div>
      </div>
    </div>
  );
}
