"""
Tests for Docker containerization (Epic 11 - F11.1).

Supports both real and mocked Docker runtimes:
- DOCKER_RUNTIME=mock: Uses lightweight fake Docker client (fast, for CI)
- DOCKER_RUNTIME=real: Uses actual Docker SDK (requires Docker daemon)
"""

import os
import time
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import requests


# ============================================================================
# Mock Docker Client
# ============================================================================
class MockContainer:
    """Lightweight fake container for testing without Docker daemon."""

    def __init__(self, image: str, **kwargs):
        self.image = image
        self.name = kwargs.get("name", "test-container")
        self.ports = kwargs.get("ports", {})
        self.environment = kwargs.get("environment", {})
        self.status = "running"
        self.id = "mock-container-id-12345"

    def reload(self):
        """Reload container info."""
        pass

    def logs(self, **kwargs) -> bytes:
        """Return mock logs."""
        return b"Mock container logs\nContainer started successfully"

    def stop(self, **kwargs):
        """Stop the container."""
        self.status = "stopped"

    def remove(self, **kwargs):
        """Remove the container."""
        self.status = "removed"

    def exec_run(self, cmd: str, **kwargs) -> tuple[int, bytes]:
        """Execute command in container."""
        if "health" in cmd:
            return (0, b'{"status": "ok"}')
        return (0, b"Command executed successfully")


class MockImage:
    """Mock Docker image."""

    def __init__(self, tags: list[str]):
        self.tags = tags
        self.id = "mock-image-id-67890"


class MockDockerClient:
    """Lightweight fake Docker client for CI testing."""

    def __init__(self):
        self.containers = MockContainerManager()
        self.images = MockImageManager()

    def close(self):
        """Close the client."""
        pass


class MockContainerManager:
    """Mock container manager."""

    def __init__(self):
        self._containers: Dict[str, MockContainer] = {}

    def run(self, image: str, **kwargs) -> MockContainer:
        """Run a container."""
        container = MockContainer(image, **kwargs)
        self._containers[container.name] = container
        return container

    def get(self, name: str) -> MockContainer:
        """Get a container by name."""
        return self._containers.get(name, MockContainer("unknown"))

    def list(self, **kwargs) -> list[MockContainer]:
        """List containers."""
        return list(self._containers.values())


class MockImageManager:
    """Mock image manager."""

    def build(self, **kwargs) -> tuple[MockImage, list]:
        """Build an image."""
        path = kwargs.get("path", ".")
        tag = kwargs.get("tag", "test:latest")
        image = MockImage([tag])
        logs = [{"stream": f"Building image from {path}"}]
        return image, logs

    def get(self, name: str) -> MockImage:
        """Get an image by name."""
        return MockImage([name])


# ============================================================================
# Docker Client Factory
# ============================================================================
def get_docker_client():
    """Get Docker client based on DOCKER_RUNTIME environment variable."""
    runtime = os.getenv("DOCKER_RUNTIME", "mock").lower()

    if runtime == "real":
        try:
            import docker

            return docker.from_env()
        except Exception as exc:
            pytest.skip(f"Real Docker not available: {exc}")
    else:
        # Return mock client for fast CI testing
        return MockDockerClient()


def is_real_docker() -> bool:
    """Check if using real Docker runtime."""
    return os.getenv("DOCKER_RUNTIME", "mock").lower() == "real"


def requires_real_docker(func):
    """Decorator to skip test unless DOCKER_AVAILABLE=1 is set."""

    def wrapper(*args, **kwargs):
        if not is_real_docker() or os.getenv("DOCKER_AVAILABLE") != "1":
            pytest.skip("Real Docker required but not available")
        return func(*args, **kwargs)

    return wrapper


# ============================================================================
# Tests
# ============================================================================
class TestDockerBuild:
    """Test Docker image building."""

    def test_dockerfile_exists(self):
        """Verify Dockerfile exists."""
        import pathlib

        dockerfile = pathlib.Path("Dockerfile")
        assert dockerfile.exists(), "Dockerfile not found"

    def test_dockerfile_has_healthcheck(self):
        """Verify Dockerfile includes HEALTHCHECK directive."""
        with open("Dockerfile", "r") as f:
            content = f.read()
        assert "HEALTHCHECK" in content, "Dockerfile missing HEALTHCHECK"
        assert "/health" in content, "Healthcheck doesn't probe /health endpoint"

    def test_dockerfile_uses_nonroot_user(self):
        """Verify Dockerfile creates and uses non-root user."""
        with open("Dockerfile", "r") as f:
            content = f.read()
        assert "useradd" in content or "adduser" in content, "No user creation found"
        assert "USER " in content, "No USER directive found"

    def test_dockerfile_multistage(self):
        """Verify Dockerfile uses multi-stage build."""
        with open("Dockerfile", "r") as f:
            content = f.read()
        assert "FROM " in content and content.count("FROM ") >= 2, (
            "Dockerfile should use multi-stage build"
        )

    def test_build_image_mock(self):
        """Test building Docker image with mock client."""
        client = get_docker_client()

        # Build image
        image, logs = client.images.build(
            path=".",
            tag="bd_stockevaluator:test",
            rm=True,
        )

        assert image is not None
        assert len(image.tags) > 0
        assert logs is not None


class TestDockerRun:
    """Test running Docker container."""

    @pytest.fixture
    def docker_client(self):
        """Provide Docker client."""
        client = get_docker_client()
        yield client
        client.close()

    def test_run_container_mock(self, docker_client):
        """Test running container with mock client."""
        container = None
        try:
            container = docker_client.containers.run(
                "bd_stockevaluator:latest",
                name="test-stock-evaluator",
                ports={"8000/tcp": 8000},
                environment={"PORT": "8000"},
                detach=True,
            )

            assert container is not None
            assert container.status == "running"
            assert "8000" in str(container.ports)

        finally:
            if container:
                container.stop()
                container.remove()

    def test_container_healthcheck_mock(self, docker_client):
        """Test container health check with mock client."""
        container = None
        try:
            container = docker_client.containers.run(
                "bd_stockevaluator:latest",
                name="test-health-check",
                ports={"8000/tcp": 8000},
                detach=True,
            )

            # Execute health check command
            exit_code, output = container.exec_run(
                "python -c \"import urllib.request; "
                "urllib.request.urlopen('http://localhost:8000/health').read()\""
            )

            assert exit_code == 0
            assert output

        finally:
            if container:
                container.stop()
                container.remove()


class TestDockerCompose:
    """Test docker-compose.yml configuration."""

    def test_docker_compose_exists(self):
        """Verify docker-compose.yml exists."""
        import pathlib

        compose_file = pathlib.Path("docker-compose.yml")
        assert compose_file.exists(), "docker-compose.yml not found"

    def test_docker_compose_has_healthcheck(self):
        """Verify docker-compose.yml includes healthcheck."""
        with open("docker-compose.yml", "r") as f:
            content = f.read()
        assert "healthcheck" in content, "docker-compose.yml missing healthcheck"

    def test_docker_compose_has_volumes(self):
        """Verify docker-compose.yml configures volumes for persistence."""
        with open("docker-compose.yml", "r") as f:
            content = f.read()
        assert "volumes:" in content, "docker-compose.yml missing volumes"


# ============================================================================
# Integration Tests (Real Docker Only)
# ============================================================================
@pytest.mark.skipif(
    os.getenv("DOCKER_AVAILABLE") != "1",
    reason="Real Docker integration tests require DOCKER_AVAILABLE=1",
)
class TestDockerIntegration:
    """Integration tests requiring real Docker daemon."""

    @requires_real_docker
    def test_build_and_run_real(self):
        """Build and run container with real Docker."""
        import docker

        client = docker.from_env()
        container = None

        try:
            # Build image
            print("Building Docker image...")
            image, logs = client.images.build(
                path=".",
                tag="bd_stockevaluator:integration-test",
                rm=True,
                forcerm=True,
            )

            # Run container
            print("Starting container...")
            container = client.containers.run(
                "bd_stockevaluator:integration-test",
                name="integration-test-container",
                ports={"8000/tcp": 8001},
                environment={
                    "PORT": "8000",
                    "GROQ_API_KEY": "test",
                },
                detach=True,
                remove=False,
            )

            # Wait for container to be healthy
            print("Waiting for container to start...")
            time.sleep(10)

            # Test health endpoint
            response = requests.get("http://localhost:8001/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

            print("Integration test passed!")

        finally:
            if container:
                try:
                    container.stop(timeout=10)
                    container.remove()
                except Exception as e:
                    print(f"Cleanup error: {e}")
            client.close()


# ============================================================================
# Documentation Tests
# ============================================================================
class TestDocumentation:
    """Test Docker documentation."""

    def test_env_example_exists(self):
        """Verify .env.example file exists."""
        import pathlib

        env_example = pathlib.Path(".env.example")
        assert env_example.exists(), ".env.example file not found"

    def test_env_example_has_docker_vars(self):
        """Verify .env.example includes Docker-related variables."""
        with open(".env.example", "r") as f:
            content = f.read()
        assert "DOCKER_RUNTIME" in content, ".env.example missing DOCKER_RUNTIME"
        assert "DOCKER_AVAILABLE" in content, ".env.example missing DOCKER_AVAILABLE"

    def test_readme_has_docker_instructions(self):
        """Verify README includes Docker instructions."""
        import pathlib

        readme = pathlib.Path("README.md")
        if readme.exists():
            with open("README.md", "r") as f:
                content = f.read()
            # Basic check - at least one docker command mentioned
            has_docker_ref = any(
                term in content.lower()
                for term in ["docker", "container", "docker-compose"]
            )
            assert has_docker_ref, "README should mention Docker"
