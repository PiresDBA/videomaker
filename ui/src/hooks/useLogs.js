import { useEffect, useState, useCallback, useRef } from "react";

const WS_URL = "ws://127.0.0.1:8765/api/logs";
const REST_URL = "http://127.0.0.1:8765/api/logs/recent?limit=200";
const MAX_LOGS = 500;

export function useLogs() {
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const retried = useRef(false);
  const hydrated = useRef(false);

  useEffect(() => {
    let ws = null;
    let closed = false;
    let reconnectTimer = null;
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
        scheduleReconnect();
        return;
      }
      ws.onopen = () => {
        retried.current = false;
        attempts = 0;
        setConnected(true);
      };
      ws.onclose = () => {
        setConnected(false);
        scheduleReconnect();
      };
      ws.onerror = () => {
        try { ws.close(); } catch (_) {}
      };
      ws.onmessage = (ev) => {
        try {
          const entry = JSON.parse(ev.data);
          setLogs((prev) => [entry, ...prev].slice(0, MAX_LOGS));
        } catch (_) {}
      };
    };

    const scheduleReconnect = () => {
      if (closed) return;
      attempts += 1;
      const delay = Math.min(8000, 1200 * attempts);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connect, delay);
    };

    connect();
    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      try { ws?.close(); } catch (_) {}
    };
  }, []);

  const clear = useCallback(() => setLogs([]), []);

  return { logs, connected, clear };
}
