"""
Docker service helpers for local infrastructure containers.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


POSTGRES_CONTAINER = "contentpilot-postgres"
SEARXNG_CONTAINER = "contentpilot-searxng"
DOCKER_PATH = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
COMPOSE_DIR = Path(__file__).resolve().parents[2]


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    try:
        proc = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(COMPOSE_DIR),
            ),
            timeout=20.0,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except asyncio.TimeoutError:
        return -1, "", "Command timed out after 20 seconds"
    except Exception as exc:
        return -1, "", str(exc)


async def _container_status(container_name: str) -> str:
    code, out, _ = await _run(["docker", "inspect", "-f", "{{.State.Status}}", container_name])
    return out if code == 0 and out else "missing"


async def _is_docker_running() -> bool:
    try:
        proc = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run,
                ["docker", "info"],
                capture_output=True,
                check=False,
            ),
            timeout=5.0,
        )
        return proc.returncode == 0
    except Exception:
        return False


async def _start_docker_desktop() -> bool:
    try:
        await asyncio.to_thread(subprocess.Popen, [DOCKER_PATH], shell=True)
        for _ in range(30):
            if await _is_docker_running():
                return True
            await asyncio.sleep(2)
        return False
    except Exception as exc:
        print(f"Failed to start Docker Desktop automatically: {exc}")
        return False


async def check_services_status(searxng_url: str | None = None) -> Dict[str, Any]:
    postgres_status = await _container_status(POSTGRES_CONTAINER)
    searxng_status = await _container_status(SEARXNG_CONTAINER)
    normalized_url = (searxng_url or "").strip().rstrip("/")
    return {
        "docker_running": await _is_docker_running(),
        "searxng_url": normalized_url,
        "postgres": {
            "container": POSTGRES_CONTAINER,
            "running": postgres_status == "running",
            "status": postgres_status,
        },
        "searxng": {
            "container": SEARXNG_CONTAINER,
            "running": searxng_status == "running",
            "status": searxng_status,
            "url": normalized_url,
        },
        "running": postgres_status == "running" and searxng_status == "running",
    }


async def start_services() -> Dict[str, Any]:
    if not await _is_docker_running():
        if os.path.exists(DOCKER_PATH):
            if not await _start_docker_desktop():
                return {"ok": False, "message": "Docker Desktop failed to start or is not ready."}
        else:
            return {"ok": False, "message": "Docker daemon is not running and Docker Desktop was not found."}

    code, _, err = await _run(["docker", "compose", "up", "-d", "postgres", "searxng"])
    if code != 0:
        return {"ok": False, "message": f"Failed to start services: {err}"}

    return {"ok": True, "message": "Postgres and SearXNG started."}


async def stop_services() -> Dict[str, Any]:
    code, _, err = await _run(["docker", "compose", "stop", "postgres", "searxng"])
    if code != 0:
        return {"ok": False, "message": f"Failed to stop services: {err}"}
    return {"ok": True, "message": "Postgres and SearXNG stopped."}
