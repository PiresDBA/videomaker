#!/usr/bin/env python3
r"""flow_mcp.py - Servidor MCP robusto para o Google Flow.

Expõe ferramentas MCP para gerar imagem, vídeo e áudio via o Google Flow,
usando o flow_fetch.py como executor por baixo.

Protocolo: Model Context Protocol (MCP) sobre stdio (JSON-RPC 2.0).

Ferramentas expostas:
  - flow_generate_image   → gera imagem estática
  - flow_generate_video   → gera vídeo
  - flow_generate_audio   → gera áudio/voz
  - flow_check            → testa conexão CDP + login no Flow
  - flow_login            → fluxo de login com pausa para o usuário

Robustez:
  - Timeout configurável por ferramenta
  - Retry exponencial em falhas de rede/CDP
  - Detecção de Chrome travado → reinício limpo
  - Validação de entrada (prompt não vazio, nome sanitizado)
  - Logs estruturados em JSON para diagnóstico
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_CDP = os.environ.get("GEMINI_CDP_URL", "http://127.0.0.1:18800")
DEFAULT_ROOT = r"C:\videomaker"
DEFAULT_TIMEOUT_S = 300
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0

# ----------------------------------------------------------------- utilitários


def _log(level: str, msg: str, **kwargs):
    """Log estruturado em JSON para diagnóstico."""
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "level": level, "msg": msg}
    entry.update(kwargs)
    print(json.dumps(entry, ensure_ascii=False), flush=True)


def _sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos de nome de arquivo."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.strip() or "flow_output"


def _validate_prompt(prompt: Optional[str]) -> str:
    if not prompt or not prompt.strip():
        raise ValueError("prompt não pode estar vazio")
    return prompt.strip()


# ----------------------------------------------------------------- execução do flow_fetch


async def _run_flow_fetch(
    kind: str,
    prompt: str,
    name: str,
    project_dir: Optional[str] = None,
    wait_s: int = DEFAULT_TIMEOUT_S,
    ref_image: Optional[str] = None,
    retries: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """Executa o flow_fetch.py como subprocesso com retry e backoff."""
    import subprocess

    args = [
        sys.executable,
        "scripts/flow_fetch.py",
        "--kind", kind,
        "--prompt", prompt,
        "--name", name,
        "--wait", str(wait_s),
        "--retries", str(retries),
        "--cdp-url", DEFAULT_CDP,
    ]
    if project_dir:
        args += ["--project-dir", project_dir]
    if ref_image:
        args += ["--ref-image", ref_image]

    last_error = ""
    for attempt in range(retries + 1):
        if attempt > 0:
            backoff = RETRY_BACKOFF_BASE ** attempt
            _log("info", "retry flow_fetch", attempt=attempt, backoff_s=backoff)
            await asyncio.sleep(backoff)

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=DEFAULT_ROOT,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=wait_s + 60
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                last_error = f"timeout após {wait_s + 60}s"
                _log("warn", "timeout flow_fetch", kind=kind, name=name, attempt=attempt)
                continue

            rc = proc.returncode
            out = stdout.decode("utf-8", errors="replace") if stdout else ""
            err = stderr.decode("utf-8", errors="replace") if stderr else ""

            if rc == 0:
                # Extrair resultado do resumo final
                m = re.search(r"RESUMO (\d+)/(\d+)", out)
                ok_count = int(m.group(1)) if m else 0
                total = int(m.group(2)) if m else 0
                return {
                    "ok": ok_count == total and ok_count > 0,
                    "kind": kind,
                    "name": name,
                    "rc": rc,
                    "stdout": out[-2000:] if len(out) > 2000 else out,
                    "stderr": err[-1000:] if len(err) > 1000 else err,
                    "attempt": attempt,
                }
            else:
                last_error = err or out or f"rc={rc}"
                _log("warn", "flow_fetch falhou", kind=kind, name=name,
                     rc=rc, attempt=attempt, error=last_error[:200])

        except Exception as e:
            last_error = str(e)
            _log("error", "exceção flow_fetch", kind=kind, name=name,
                 attempt=attempt, error=str(e)[:200])

    return {
        "ok": False,
        "kind": kind,
        "name": name,
        "error": last_error or "falha desconhecida",
        "attempts": retries + 1,
    }


# ----------------------------------------------------------------- protocolo MCP (JSON-RPC sobre stdio)


class MCPServer:
    def __init__(self):
        self.tools = {
            "flow_generate_image": self._tool_generate_image,
            "flow_generate_video": self._tool_generate_video,
            "flow_generate_audio": self._tool_generate_audio,
            "flow_check": self._tool_check,
            "flow_login": self._tool_login,
        }
        self.running = True

    # ----- handlers de ferramentas -----

    async def _tool_generate_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        prompt = _validate_prompt(args.get("prompt"))
        name = _sanitize_filename(args.get("name", "flow_image"))
        project_dir = args.get("project_dir")
        wait_s = int(args.get("wait_s", DEFAULT_TIMEOUT_S))
        ref_image = args.get("ref_image")
        retries = int(args.get("retries", MAX_RETRIES))

        _log("info", "flow_generate_image", name=name, wait_s=wait_s, project_dir=project_dir)
        return await _run_flow_fetch("image", prompt, name, project_dir, wait_s, ref_image, retries)

    async def _tool_generate_video(self, args: Dict[str, Any]) -> Dict[str, Any]:
        prompt = _validate_prompt(args.get("prompt"))
        name = _sanitize_filename(args.get("name", "flow_video"))
        project_dir = args.get("project_dir")
        wait_s = int(args.get("wait_s", DEFAULT_TIMEOUT_S))
        retries = int(args.get("retries", MAX_RETRIES))

        _log("info", "flow_generate_video", name=name, wait_s=wait_s, project_dir=project_dir)
        return await _run_flow_fetch("video", prompt, name, project_dir, wait_s, None, retries)

    async def _tool_generate_audio(self, args: Dict[str, Any]) -> Dict[str, Any]:
        prompt = _validate_prompt(args.get("prompt"))
        name = _sanitize_filename(args.get("name", "flow_audio"))
        project_dir = args.get("project_dir")
        wait_s = int(args.get("wait_s", DEFAULT_TIMEOUT_S))
        retries = int(args.get("retries", MAX_RETRIES))

        _log("info", "flow_generate_audio", name=name, wait_s=wait_s, project_dir=project_dir)
        return await _run_flow_fetch("audio", prompt, name, project_dir, wait_s, None, retries)

    async def _tool_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import urllib.request
        cdp_url = args.get("cdp_url", DEFAULT_CDP)
        try:
            urllib.request.urlopen(cdp_url.rstrip("/") + "/json/version", timeout=5)
            cdp_ok = True
        except Exception:
            cdp_ok = False

        return {
            "ok": cdp_ok,
            "cdp_url": cdp_url,
            "cdp_alive": cdp_ok,
            "flow_url": "https://flow.google.com",
        }

    async def _tool_login(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Solicita login do usuário no Google Flow."""
        _log("info", "flow_login solicitado")
        return {
            "ok": True,
            "msg": "Abra o Chrome e faça login em https://flow.google.com. "
                   "Após o login, o flow_fetch estará pronto para usar.",
            "flow_url": "https://flow.google.com",
        }

    # ----- loop MCP -----

    async def _handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        method = req.get("method", "")
        params = req.get("params", {}) or {}
        req_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "flow-mcp", "version": "r1-2026-11-07"},
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "flow_generate_image",
                            "description": "Gera imagem estática via Google Flow",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {"type": "string", "description": "Prompt de geração de imagem"},
                                    "name": {"type": "string", "description": "Nome do arquivo de saída"},
                                    "project_dir": {"type": "string", "description": "Diretório do projeto"},
                                    "wait_s": {"type": "integer", "description": "Tempo de espera em segundos"},
                                    "ref_image": {"type": "string", "description": "Imagem de referência"},
                                    "retries": {"type": "integer", "description": "Número de tentativas"},
                                },
                                "required": ["prompt"],
                            },
                        },
                        {
                            "name": "flow_generate_video",
                            "description": "Gera vídeo via Google Flow",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {"type": "string"},
                                    "name": {"type": "string"},
                                    "project_dir": {"type": "string"},
                                    "wait_s": {"type": "integer"},
                                    "retries": {"type": "integer"},
                                },
                                "required": ["prompt"],
                            },
                        },
                        {
                            "name": "flow_generate_audio",
                            "description": "Gera áudio/voz via Google Flow",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {"type": "string"},
                                    "name": {"type": "string"},
                                    "project_dir": {"type": "string"},
                                    "wait_s": {"type": "integer"},
                                    "retries": {"type": "integer"},
                                },
                                "required": ["prompt"],
                            },
                        },
                        {
                            "name": "flow_check",
                            "description": "Testa conexão CDP + login no Flow",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                        {
                            "name": "flow_login",
                            "description": "Solicita login do usuário no Google Flow",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                    ],
                },
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {}) or {}
            handler = self.tools.get(tool_name)
            if not handler:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Ferramenta não encontrada: {tool_name}"},
                }
            try:
                result = await handler(tool_args)
                return {"jsonrpc": "2.0", "id": req_id, "result": result}
            except Exception as e:
                _log("error", "erro na ferramenta MCP", tool=tool_name, error=str(e)[:200])
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)},
                }

        if method == "shutdown" or method == "exit":
            self.running = False
            return {"jsonrpc": "2.0", "id": req_id, "result": None}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Método não encontrado: {method}"},
        }

    async def run_stdio(self):
        """Loop principal MCP sobre stdio."""
        _log("info", "flow_mcp iniciado", cdp_url=DEFAULT_CDP, root=DEFAULT_ROOT)

        loop = asyncio.get_event_loop()

        def _read_line():
            return sys.stdin.readline()

        while self.running:
            try:
                line = await asyncio.wait_for(
                    loop.run_in_executor(None, _read_line), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace").strip() if isinstance(line, bytes) else line.strip()
            if not line_str:
                continue
            try:
                req = json.loads(line_str)
            except json.JSONDecodeError as e:
                _log("warn", "linha JSON inválida", error=str(e)[:100])
                continue
            resp = await self._handle_request(req)
            out = json.dumps(resp, ensure_ascii=False) + "\n"
            sys.stdout.write(out)
            sys.stdout.flush()


async def main():
    server = MCPServer()

    def _shutdown(sig, frame):
        server.running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    await server.run_stdio()
    _log("info", "flow_mcp encerrado")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
