"""taskyn-ui — start/stop the Taskyn web UI stack (backend + frontend)."""

from __future__ import annotations

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import typer

app = typer.Typer(
    name="taskyn-ui",
    help="Start and stop the Taskyn web UI stack.",
    no_args_is_help=True,
)

BACKEND_PORT = 5020
FRONTEND_PORT = 3020

# Resolve paths relative to this file so the command works from any directory.
_THIS_DIR = Path(__file__).parent
_BACKEND_MODULE = "taskyn.web.backend.main:app"
_FRONTEND_DIR = _THIS_DIR / "frontend"

# Windows: suppress console window for background processes.
_CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _kill_port(port: int) -> bool:
    """Kill whichever process is listening on *port*. Returns True if something was killed."""
    killed = False

    # Try psutil first — clean and cross-platform.
    try:
        import psutil  # type: ignore

        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status in ("LISTEN", "ESTABLISHED"):
                try:
                    proc = psutil.Process(conn.pid)
                    proc.kill()
                    killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return killed
    except ImportError:
        pass

    # Fallback: parse `netstat -ano` on Windows.
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                creationflags=_CREATION_FLAGS,
            )
            pids: set[str] = set()
            for line in result.stdout.splitlines():
                parts = line.split()
                # Format: Proto  Local Address  Foreign Address  State  PID
                if len(parts) >= 5 and f":{port}" in parts[1]:
                    pids.add(parts[-1])
            for pid in pids:
                subprocess.run(
                    ["taskkill", "/F", "/PID", pid],
                    capture_output=True,
                    creationflags=_CREATION_FLAGS,
                )
                killed = True
        except Exception:
            pass
        return killed

    # Fallback: lsof on Unix/macOS.
    try:
        result = subprocess.run(
            ["lsof", "-t", f"-i:{port}"],
            capture_output=True,
            text=True,
        )
        for pid_str in result.stdout.split():
            subprocess.run(["kill", "-9", pid_str], capture_output=True)
            killed = True
    except Exception:
        pass

    return killed


@app.command()
def start() -> None:
    """Start the backend and frontend, then open the browser."""
    typer.echo("Starting Taskyn UI…")

    # --- Backend (uvicorn) ---
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        _BACKEND_MODULE,
        "--host",
        "127.0.0.1",
        "--port",
        str(BACKEND_PORT),
    ]
    subprocess.Popen(
        backend_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_CREATION_FLAGS,
    )

    # --- Frontend (Vite via npx) ---
    npx_exe = "npx.cmd" if sys.platform == "win32" else "npx"
    frontend_cmd = [npx_exe, "vite", "--port", str(FRONTEND_PORT)]
    subprocess.Popen(
        frontend_cmd,
        cwd=str(_FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_CREATION_FLAGS,
    )

    # Give the services a moment to bind their ports.
    time.sleep(3)

    webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
    typer.echo(
        f"Taskyn UI running — backend:{BACKEND_PORT}, frontend:{FRONTEND_PORT}"
    )


@app.command()
def stop() -> None:
    """Kill the backend and frontend processes."""
    backend_stopped = _kill_port(BACKEND_PORT)
    frontend_stopped = _kill_port(FRONTEND_PORT)

    if not backend_stopped and not frontend_stopped:
        typer.echo("No Taskyn UI processes found.")
    else:
        typer.echo("Taskyn UI stopped.")
