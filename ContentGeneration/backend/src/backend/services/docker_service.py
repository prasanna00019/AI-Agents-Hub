"""
Docker service for managing the SearXNG container.

Uses subprocess to control docker containers. The SearXNG service
definition lives in the project's docker-compose.yml, but this module
lets the user start/stop just the SearXNG container from the UI.
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any, Dict


CONTAINER_NAME = "contentpilot-searxng"
IMAGE = "docker.io/searxng/searxng:latest"
HOST_PORT = 8080


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a subprocess command asynchronously."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


async def check_searxng_status() -> Dict[str, Any]:
    """Check if the SearXNG container is running."""
    code, out, _ = await _run([
        "docker", "inspect", "-f", "{{.State.Status}}", CONTAINER_NAME
    ])
    if code == 0 and out == "running":
        return {"running": True, "container": CONTAINER_NAME, "port": HOST_PORT}
    return {"running": False, "container": CONTAINER_NAME, "port": HOST_PORT}


async def start_searxng() -> Dict[str, Any]:
    """Start the SearXNG Docker container."""
    # Check if already running
    status = await check_searxng_status()
    if status["running"]:
        return {"ok": True, "message": "SearXNG is already running", **status}

    # Try to start existing stopped container
    code, _, _ = await _run(["docker", "start", CONTAINER_NAME])
    if code == 0:
        return {"ok": True, "message": "SearXNG container started", "running": True}

    # Create new container
    code, out, err = await _run([
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "-p", f"{HOST_PORT}:8080",
        "-e", "SEARXNG_BASE_URL=http://localhost:8080/",
        "--restart", "unless-stopped",
        IMAGE,
    ])

    if code == 0:
        return {"ok": True, "message": "SearXNG container created and started", "running": True}
    return {"ok": False, "message": f"Failed to start: {err}", "running": False}


async def stop_searxng() -> Dict[str, Any]:
    """Stop the SearXNG Docker container."""
    code, _, err = await _run(["docker", "stop", CONTAINER_NAME])
    if code != 0:
        return {"ok": False, "message": f"Failed to stop: {err}"}

    # Remove container so it can be recreated cleanly
    await _run(["docker", "rm", CONTAINER_NAME])
    return {"ok": True, "message": "SearXNG container stopped and removed", "running": False}
