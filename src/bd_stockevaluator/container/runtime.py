"""Runtime helpers for Docker-backed workflows.

Epic 11 requires the application to support both real Docker execution and a
fast mock mode for CI. This module exposes a single entry point,
``get_docker_client()``, that inspects the ``DOCKER_RUNTIME`` environment
variable and returns the appropriate client implementation.

When ``DOCKER_RUNTIME`` is ``"real"`` we delegate to the Docker SDK;
otherwise we fall back to an in-memory mock that records call metadata without
making external calls. The indirection makes it trivial for unit tests and CI
pipelines to exercise container flows without requiring a Docker daemon, while
still enabling opt-in real-engine coverage locally or in nightly jobs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:  # pragma: no cover - import failure exercised via tests
    import docker as _docker
except Exception:  # pragma: no cover - docker not available in CI by default
    _docker = None


@dataclass
class MockContainer:
    """Lightweight stand-in for docker.models.containers.Container."""

    image: str
    command: Optional[str] = None
    name: Optional[str] = None
    environment: Dict[str, Any] = field(default_factory=dict)
    status: str = "created"

    def logs(self) -> bytes:
        return b""

    def stop(self, timeout: int | float | None = None) -> None:  # pragma: no cover - noop
        self.status = "exited"

    def remove(self, force: bool = False) -> None:  # pragma: no cover - noop
        self.status = "removed"


class MockContainerCollection:
    """Minimal container collection mimicking docker-py behaviour."""

    def __init__(self) -> None:
        self._created: list[MockContainer] = []

    def run(self, image: str, command: str | None = None, **kwargs: Any) -> MockContainer:
        container = MockContainer(
            image=image,
            command=command,
            name=kwargs.get("name"),
            environment=kwargs.get("environment", {}),
        )
        container.status = "running"
        self._created.append(container)
        return container

    def list(self) -> list[MockContainer]:  # pragma: no cover - convenience helper
        return list(self._created)


@dataclass
class MockImage:
    """Captures build metadata for assertions."""

    tags: list[str]


class MockImageCollection:
    """Records build calls without invoking Docker."""

    def __init__(self) -> None:
        self._builds: list[dict[str, Any]] = []

    def build(self, path: str = ".", tag: str | None = None, **kwargs: Any) -> tuple[list[dict[str, Any]], MockImage]:
        record = {"path": path, "tag": tag, "options": kwargs}
        self._builds.append(record)
        image = MockImage(tags=[tag or "mock:latest"])
        return self._builds, image

    def history(self) -> list[dict[str, Any]]:  # pragma: no cover - convenience helper
        return list(self._builds)


class MockDockerClient:
    """Composite mock exposing ``containers`` and ``images`` collections."""

    def __init__(self) -> None:
        self.containers = MockContainerCollection()
        self.images = MockImageCollection()

    def ping(self) -> bool:
        return True

    def close(self) -> None:  # pragma: no cover - noop
        return None


_CLIENT_CACHE: dict[str, Any] = {}


def _create_real_docker_client() -> Any:
    """Instantiate a docker SDK client, raising if unavailable."""

    if _docker is None:
        raise RuntimeError(
            "Docker SDK is not installed. Install 'docker' or set DOCKER_RUNTIME=mock."
        )
    return _docker.from_env()


def _normalise_runtime(value: Optional[str]) -> str:
    if not value:
        return "mock"
    return value.strip().lower()


def get_docker_client(force_refresh: bool = False) -> Any:
    """Return the configured Docker client based on ``DOCKER_RUNTIME``.

    Parameters
    ----------
    force_refresh:
        When ``True`` the cached client is ignored and a new instance is created.

    Raises
    ------
    ValueError
        If ``DOCKER_RUNTIME`` is set to an unsupported value.
    RuntimeError
        If the Docker SDK is unavailable while ``DOCKER_RUNTIME=real``.
    """

    runtime = _normalise_runtime(os.environ.get("DOCKER_RUNTIME"))

    valid = {"mock", "real"}
    if runtime not in valid:
        raise ValueError(
            f"Unsupported DOCKER_RUNTIME '{runtime}'. Expected one of {sorted(valid)}."
        )

    if not force_refresh:
        cached = _CLIENT_CACHE.get(runtime)
        if cached is not None:
            return cached

    if runtime == "real":
        client = _create_real_docker_client()
    else:
        client = MockDockerClient()

    _CLIENT_CACHE[runtime] = client
    return client


__all__ = ["MockDockerClient", "get_docker_client"]
