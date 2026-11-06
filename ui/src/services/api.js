const API_BASE = "";

export async function apiRequest(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => apiRequest("/api/health"),
  runPipeline: (body) => apiRequest("/api/pipeline/run", { method: "POST", body: JSON.stringify(body) }),
  resumePipeline: (slug, force, fromPhase) =>
    apiRequest(`/api/pipeline/resume?slug=${encodeURIComponent(slug)}${force ? "&force=1" : ""}${fromPhase ? "&from_phase=" + encodeURIComponent(fromPhase) : ""}`, { method: "POST" }),
  stopPipeline: (runId) => apiRequest(`/api/pipeline/stop/${runId}`, { method: "POST" }),
  stopAllPipelines: () => apiRequest("/api/pipeline/stop-all", { method: "POST" }),
  pipelineStatus: (runId) => apiRequest(`/api/pipeline/status/${runId}`),
  pipelineRuns: () => apiRequest("/api/pipeline/runs"),
  projects: () => apiRequest("/api/projects"),
  projectStatus: (slug) => apiRequest(`/api/projects/${encodeURIComponent(slug)}/status`),
  dailyRun: (opts = {}) => apiRequest("/api/daily/run", { method: "POST", body: JSON.stringify(opts) }),
  dailyStatus: () => apiRequest("/api/daily/status"),
  dailyStopAgent: () => apiRequest("/api/daily/stop-agent", { method: "POST" }),
  dailyAgentStatus: () => apiRequest("/api/daily/agent-status"),
  dailyUnpauseRequeue: () => apiRequest("/api/daily/unpause-requeue", { method: "POST" }),
  schedules: () => apiRequest("/api/schedules"),
  createSchedule: (body) => apiRequest("/api/schedules", { method: "POST", body: JSON.stringify(body) }),
  deleteSchedule: (id) => apiRequest(`/api/schedules/${id}`, { method: "DELETE" }),
  markScheduleDone: (id) => apiRequest(`/api/schedules/${id}/done`, { method: "POST" }),
  topics: () => apiRequest("/api/topics"),
  telemetry: () => apiRequest("/api/telemetry"),
  logsRecent: (limit = 200) => apiRequest(`/api/logs/recent?limit=${limit}`),
  getSettings: () => apiRequest("/api/settings"),
  putSettings: (body) => apiRequest("/api/settings", { method: "PUT", body: JSON.stringify(body) }),
};
