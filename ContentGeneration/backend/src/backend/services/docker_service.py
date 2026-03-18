"""
Docker service for managing the SearXNG container.

The container runtime config is driven by the URL saved from the frontend.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any, Dict
from urllib.parse import urlparse


CONTAINER_NAME = "contentpilot-searxng"
IMAGE = "docker.io/searxng/searxng:latest"
DOCKER_PATH = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    try:
        proc = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=False,
            ),
            timeout=10.0,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except asyncio.TimeoutError:
        return -1, "", "Command timed out after 10 seconds"
    except Exception as exc:
        return -1, "", str(exc)


def _normalize_searxng_url(searxng_url: str | None) -> str:
    return (searxng_url or "").strip().rstrip("/")


def _resolve_host_port(searxng_url: str | None) -> int | None:
    normalized = _normalize_searxng_url(searxng_url)
    if not normalized:
        return None
    parsed = urlparse(normalized)
    return parsed.port


def _config_payload(searxng_url: str | None) -> Dict[str, Any]:
    normalized = _normalize_searxng_url(searxng_url)
    port = _resolve_host_port(normalized)
    return {
        "configured": bool(normalized),
        "url": normalized,
        "port": port,
        "controllable": port is not None,
    }


async def _remove_existing_container() -> None:
    await _run(["docker", "stop", CONTAINER_NAME])

async def _container_exists() -> bool:
    code, out, _ = await _run(["docker", "ps", "-a", "-q", "-f", f"name={CONTAINER_NAME}"])
    return code == 0 and bool(out.strip())


async def check_searxng_status(searxng_url: str | None = None) -> Dict[str, Any]:
    config = _config_payload(searxng_url)
    code, out, _ = await _run(["docker", "inspect", "-f", "{{.State.Status}}", CONTAINER_NAME])
    if code == 0 and out == "running":
        return {"running": True, "container": CONTAINER_NAME, **config}
    return {"running": False, "container": CONTAINER_NAME, **config}


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
    """Attempts to start Docker Desktop and waits until it is ready."""
    try:
        # Launch Docker Desktop
        await asyncio.to_thread(subprocess.Popen, [DOCKER_PATH], shell=True)
        
        # Wait until Docker is ready (up to 60 seconds)
        for _ in range(30):
            if await _is_docker_running():
                return True
            await asyncio.sleep(2)
            
        return False
    except Exception as exc:
        print(f"Failed to start Docker Desktop automatically: {exc}")
        return False


async def start_searxng(searxng_url: str | None = None) -> Dict[str, Any]:
    config = _config_payload(searxng_url)
    if not config["configured"]:
        return {
            "ok": False,
            "message": "SearXNG URL is not configured. Save it in Settings first.",
            "running": False,
            "container": CONTAINER_NAME,
            **config,
        }
    if not config["controllable"]:
        return {
            "ok": False,
            "message": "SearXNG URL must include an explicit port to control the Docker container.",
            "running": False,
            "container": CONTAINER_NAME,
            **config,
        }

    status = await check_searxng_status(config["url"])
    if status["running"]:
        return {"ok": True, "message": "SearXNG is already running", **status}

    # Auto-start Docker Desktop if it is not running
    if not await _is_docker_running():
        if os.path.exists(DOCKER_PATH):
            started = await _start_docker_desktop()
            if not started:
                return {
                    "ok": False,
                    "message": "Docker Desktop failed to start or isn't ready. Please start it manually.",
                    "running": False,
                    "container": CONTAINER_NAME,
                    **config,
                }
        else:
            return {
                "ok": False,
                "message": "Docker daemon is not running and Docker Desktop was not found at the default path.",
                "running": False,
                "container": CONTAINER_NAME,
                **config,
            }

    exists = await _container_exists()

    if exists:
        code, _, err = await _run(["docker", "start", CONTAINER_NAME])
    else:
        code, _, err = await _run([
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-p",
            f"{config['port']}:8080",
            "-e",
            f"SEARXNG_BASE_URL={config['url']}/",
            "-e",
            "SEARXNG_SETTINGS_SEARCH_FORMATS=html,json",
            "--restart",
            "unless-stopped",
            IMAGE,
        ])

    if code == 0:
        return {
            "ok": True,
            "message": "SearXNG container created and started",
            "running": True,
            "container": CONTAINER_NAME,
            **config,
        }
    return {
        "ok": False,
        "message": f"Failed to start: {err}",
        "running": False,
        "container": CONTAINER_NAME,
        **config,
    }


async def stop_searxng(searxng_url: str | None = None) -> Dict[str, Any]:
    config = _config_payload(searxng_url)
    code, _, err = await _run(["docker", "stop", CONTAINER_NAME])
    if code != 0:
        return {
            "ok": False,
            "message": f"Failed to stop: {err}",
            "running": False,
            "container": CONTAINER_NAME,
            **config,
        }

    await _remove_existing_container()
    return {
        "ok": True,
        "message": "SearXNG container stopped and removed",
        "running": False,
        "container": CONTAINER_NAME,
        **config,
    }
